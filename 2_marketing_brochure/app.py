
import os
import requests
import json
from typing import List
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from IPython.display import Markdown, display, update_display
from openai import OpenAI

# ====================================================================
# Initialize and constants

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if api_key and api_key.startswith('sk-proj-') and len(api_key)>10:
    print("API key looks good so far")
else:
    print("There might be a problem with your API key? Please visit the troubleshooting notebook!")
    
MODEL = 'gpt-4o-mini'
openai = OpenAI()

# A class to represent a Webpage

# Some websites need you to use proper headers when fetching them:
headers = {
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

class Website:
    """
    A utility class to represent a Website that we have scraped, now with links
    """

    def __init__(self, url):
        self.url = url
        response = requests.get(url, headers=headers)
        self.body = response.content
        soup = BeautifulSoup(self.body, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"
        if soup.body:
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""
        links = [link.get('href') for link in soup.find_all('a')]
        self.links = [link for link in links if link]

    def get_contents(self):
        return f"Webpage Title:\n{self.title}\nWebpage Contents:\n{self.text}\n\n"
    
# ==========================================================================
# First step: Have GPT-4o-mini figure out which links are relevant

# Use a call to gpt-4o-mini to read the links on a webpage, and respond in structured JSON.


link_system_prompt = "You are provided with a list of links found on a webpage. \
You are able to decide which of the links would be most relevant to include in a brochure about the company, \
such as links to an About page, or a Company page, or Careers/Jobs pages.\n"
link_system_prompt += "You should respond in JSON as in this example:"
link_system_prompt += """
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page": "url": "https://another.full.url/careers"},
        {"type": "subsidiaries page": "url": "https://another.full.url/staffelio"},
    ]
}
"""


def get_links_user_prompt(website):
    user_prompt = f"Here is the list of links on the website of {website.url} - "
    user_prompt += "please decide which of these are relevant web links for a brochure about the company, respond with the full https URL in JSON format. \
Do not include Terms of Service, Privacy, email links.\n"
    user_prompt += "Links (some might be relative links):\n"
    user_prompt += "\n".join(website.links)
    return user_prompt


def get_links(url):
    """It should decide which links are relevant, and replace relative link such as "/about" with "https://company.com/about".
    We will use "one shot prompting" in which we provide an example of how it should respond in the prompt.

    This is an excellent use case for an LLM, because it requires nuanced understanding. Imagine trying to code this without LLMs by parsing and analyzing the webpage - it would be very hard!"""
    website = Website(url)
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": link_system_prompt},
            {"role": "user", "content": get_links_user_prompt(website)}
      ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    return json.loads(result)

# ====================================================================
# Second step: make the brochure!

def get_all_details(url):
    result = "Landing page:\n"
    result += Website(url).get_contents()
    links = get_links(url)
    print("Found links:", links)
    for link in links["links"]:
        result += f"\n\n{link['type']}\n"
        result += Website(link["url"]).get_contents()
    return result

system_prompt = "You are an assistant that analyzes the contents of several relevant pages from a company website \
and creates a short brochure about the company for prospective customers, investors and recruits. Respond in markdown.\
Include details of company culture, customers and careers/jobs if you have the information.\
Adopt a clear and sympathical tone but professional"

# Or for a more humorous brochure - this demonstrates how easy it is to incorporate 'tone':

# system_prompt = "You are an assistant that analyzes the contents of several relevant pages from a company website \
# and creates a short humorous, entertaining, jokey brochure about the company for prospective customers, investors and recruits. Respond in markdown.\
# Include details of company culture, customers and careers/jobs if you have the information."

def get_brochure_user_prompt(company_name, url):
    user_prompt = f"You are looking at a company called: {company_name}\n"
    user_prompt += f"Here are the contents of its landing page and other relevant pages; use this information to build a short brochure in French of the company in markdown. Use a marketing style adapted for frech market.\n"
    user_prompt += get_all_details(url)
    user_prompt = user_prompt[:15_000] # Truncate if more than 5,000 characters
    return user_prompt

def create_brochure(company_name: str, url: str, output_path: str = None) -> str:
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_brochure_user_prompt(company_name, url)}
          ],
    )
    result = response.choices[0].message.content
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        #print(f"Brochure sauvegardée dans {output_path}")
    # else:
    #     print(result)
    return result

# ====================================================================
# Third step : translate in French

def translate_to_french(text, model="gpt-4o-mini"):
    """
    Traduit le texte donné en français en utilisant OpenAI.
    Args:
        text (str): Texte à traduire (Markdown accepté)
        model (str): Modèle OpenAI à utiliser
    Returns:
        str: Texte traduit en français
    """
    system_prompt = "Tu es un assistant de traduction. Traduis le texte en français, en conservant la mise en forme Markdown si présente."
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

# ======================================================================================
# AMELIORATION - ajout de stream

# pour streamer on ajoute dans le prompt la traduction en fançais. Sinon si chainage, perte du stream. 

def stream_brochure_chunks(company_name, url):
    """
    Generator qui stream les morceaux de texte renvoyés par l'API OpenAI.
    """
    stream = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_brochure_user_prompt(company_name, url)}
        ],
        stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ''
        if delta:
            yield delta


# ====================================================================
# Main

url = "https://www.octime.com"
print(get_links(url))
print(get_all_details(url))
# brochure_en = create_brochure("Octime", url, output_path="2_marketing_brochure/brochure_octime.md")
# brochure_fr = translate_to_french(brochure_en)
# print(brochure_fr)
# Utilisation "consommateur" :

# for token in stream_brochure_chunks("Octime", "https://octime.com"):
#     print(token, end='', flush=True)

with open("brochure.md", "w", encoding="utf-8") as f:
    for token in stream_brochure_chunks("Octime", "https://octime.com"):
        print(token, end='', flush=True)
        f.write(token)
        f.flush()

"""
# Octime - Optimisez la gestion de vos ressources humaines

## Qui sommes-nous ?

Le **Groupe Octime** est un leader en solutions de gestion du temps et de planification des ressources humaines, fort de 25 ans d’expérience. Nous développons des outils modulables adaptés tant aux TPE qu'aux grandes entreprises, visant une amélioration significative de la performance organisationnelle.

Avec **OCTIME**, **OCTIME Expresso**, et **STAFFELIO**, nous vous offrons des solutions innovantes pour la gestion des temps, des plannings, des absences, et bien plus.

## Nos solutions

### OCTIME
Une solution modulaire pour s’adapter à toutes vos spécificités métiers. Optimisez la gestion des heures, des absences, et des congés avec un suivi sécurisé et paramétrable.

### OCTIME Expresso
Une solution clé en main, parfaite pour les structures de 10 à 200 employés. Simple à utiliser, cette solution est conçue pour vous faire gagner du temps avec un minimum d’effort.

### STAFFELIO
Gestion intégrée des remplacements et des renforts, permettant de faciliter la planification opérationnelle tout en respectant les normes en vigueur.

## Notre approche unique

Notre philosophie repose sur un **accompagnement** de proximité. Nos équipes d’experts sont là pour piloter votre projet et s’assurer de sa réussite. Grâce à un service client réactif et un support technique disponible 24h/24, nous garantissons une relation durable et de confiance.

### Les témoignages de nos clients

> *"OCTIME simplifie la gestion des plannings et des remplacements, nous permettant de mieux accompagner nos équipes."*  
> — Hélène Jacq, Cadre de santé

> *"Une solution parfaitement adaptée à nos besoins, sans nécessiter de développements supplémentaires."*  
> — Pierre Bariat, Responsable administratif et financier

## Rejoignez notre équipe

Le Groupe Octime est en pleine croissance et recrute régulièrement des talents. Si vous cherchez à rejoindre une équipe dynamique dans un environnement innovant, **visitez notre site** pour en savoir plus sur nos opportunités de carrière.

## Contactez-nous

Pour plus d'informations ou pour demander une démo de nos solutions, n'hésitez pas à **nous contacter** :

**Téléphone :** 05 59 38 26 66  
**Adresse :** 2, Allée de l’innovation, 64300 Biron  
**Email :** [Contactez-nous](mailto:contact@octime.com)

---

**Optimisez votre gestion des temps RH avec le Groupe Octime - Rejoignez notre communauté de 1,6 millions d'utilisateurs !**
"""



"""['https://www.octime.com', '#', 'https://www.octime.com/logiciel-de-gestion-des-temps-octime/', 'https://www.octime.com/expresso/', 'https://www.octime.com/staffelio-solution-de-gestion-des-remplacements-du-personnel/', 'https://www.octime.com/academie-digitale-octime-formation-digitale/', 'https://www.octime.com/formations-presentielles/', 'https://www.octime.com/la-formation-octime-expresso-decouvrez-notre-programme/', 'https://www.octime.com/gestion-des-temps/', 'https://www.octime.com/planification/', 'https://www.octime.com/gestion-des-absences/', 'https://www.octime.com/badgeage/', 'https://www.octime.com/badgeuse-pointeuse/', 'https://www.octime.com/gestion-des-activites/', 'https://www.octime.com/interface-rh-paie/', 'https://www.octime.com/myoctime-application-mobile/', 'https://www.octime.com/nos-atouts/', 'https://www.octime.com/25-ans-du-groupe-octime/', 'https://www.octime.com/le-groupe-octime/', 'https://www.octime.com/alliances-sirh/', 'https://www.octime.com/amoa/', 'https://www.octime.com/nos-references/', 'https://www.octime.com/temoignages/', 'https://www.octime.com/carrieres/', 'https://www.octime.com/support-client/', '#', 'tel:0559382666', 'https://fr.linkedin.com/company/groupeoctime', 'https://www.facebook.com/groupeoctime', 'https://twitter.com/GroupeOctime', '#', 'https://www.octime.com/actualites/', 'https://www.octime.com/contact/', 'https://www.octime.com/demonstration-gratuite/', 'https://www.octime.com', '#', 'https://www.octime.com/logiciel-de-gestion-des-temps-octime/', 'https://www.octime.com/expresso/', 'https://www.octime.com/staffelio-solution-de-gestion-des-remplacements-du-personnel/', 'https://www.octime.com/academie-digitale-octime-formation-digitale/', 'https://www.octime.com/formations-presentielles/', 'https://www.octime.com/la-formation-octime-expresso-decouvrez-notre-programme/', 'https://www.octime.com/gestion-des-temps/', 'https://www.octime.com/planification/', 'https://www.octime.com/gestion-des-absences/', 'https://www.octime.com/badgeage/', 'https://www.octime.com/badgeuse-pointeuse/', 'https://www.octime.com/gestion-des-activites/', 'https://www.octime.com/interface-rh-paie/', 'https://www.octime.com/myoctime-application-mobile/', 'https://www.octime.com/nos-atouts/', 'https://www.octime.com/25-ans-du-groupe-octime/', 'https://www.octime.com/le-groupe-octime/', 'https://www.octime.com/alliances-sirh/', 'https://www.octime.com/amoa/', 'https://www.octime.com/nos-references/', 'https://www.octime.com/temoignages/', 'https://www.octime.com/carrieres/', 'https://www.octime.com/support-client/', 'https://www.octime.com/logiciel-de-gestion-des-temps-octime/', 'https://www.octime.com/expresso/', 'https://www.octime.com/staffelio-solution-de-gestion-des-remplacements-du-personnel/', 'https://www.octime.com/academie-digitale-octime-formation-digitale/', 'https://www.octime.com/formations-presentielles/', 'https://www.octime.com/la-formation-octime-expresso-decouvrez-notre-programme/', 'https://www.octime.com/gestion-des-temps/', 'https://www.octime.com/planification/', 'https://www.octime.com/logiciel-gestion-absences-et-conges/', 'https://www.octime.com/badgeage/', 'https://www.octime.com/badgeuse-pointeuse/', 'https://www.octime.com/gestion-des-activites/', 'https://www.octime.com/interface-rh-paie/', 'https://www.octime.com/myoctime-application-mobile/', 'https://www.octime.com/logiciel-de-gestion-des-temps-octime/', 'https://www.octime.com/expresso/', 'https://www.octime.com/staffelio-solution-de-gestion-des-remplacements-du-personnel/', 'https://www.octime.com/academie-digitale-octime-formation-digitale/', 'https://www.octime.com/formations-presentielles/', 'https://www.octime.com/la-formation-octime-expresso-decouvrez-notre-programme/', 'https://www.octime.com/gestion-des-temps/', 'https://www.octime.com/planification/', 'https://www.octime.com/gestion-des-absences/', 'https://www.octime.com/badgeage/', 'https://www.octime.com/badgeuse-pointeuse/', 'https://www.octime.com/gestion-des-activites/', 'https://www.octime.com/interface-rh-paie/', 'https://www.octime.com/myoctime-application-mobile/', 'https://www.octime.com/nos-atouts/', 'https://www.octime.com/25-ans-du-groupe-octime/', 'https://www.octime.com/le-groupe-octime/', 'https://www.octime.com/alliances-sirh/', 'https://www.octime.com/amoa/', 'https://www.octime.com/nos-references/', 'https://www.octime.com/temoignages/', 'https://www.octime.com/carrieres/', 'https://www.octime.com/support-client/', '/demonstration-gratuite/', 'https://www.youtube.com/watch?v=ufS-opNBbAU&width=960&height=540', 'https://www.octime.com/le-nouvel-octime/', 'https://www.octime.com/le-nouvel-octime/', '/logiciel-de-gestion-des-temps-octime/', 'https://www.octime.com/expresso/', 'https://www.octime.com/staffelio-solution-de-gestion-des-remplacements-du-personnel/', 'https://www.octime.com/gestion-des-temps/', 'https://www.octime.com/planification/', 'https://www.octime.com/planification/', 'https://www.octime.com/gestion-des-absences/', 'https://www.octime.com/badgeage/', 'https://www.octime.com/badgeuse-pointeuse/', 'https://www.octime.com/badgeage/', 'https://www.octime.com/badgeuse-pointeuse/', '/nos-atouts/', '/nos-references/', 'https://www.octime.com/category/temoignages-clients/', '/je-demarre/', '/contact/', 'https://www.linkedin.com/company/groupeoctime/', 'https://www.facebook.com/groupeoctime', 'https://twitter.com/GroupeOctime', 'https://youtube.com/@GroupeOctime', 'https://www.instagram.com/staffelio/?hl=fr', 'https://www.octime.com/logiciel-de-gestion-des-temps-octime/', 'https://www.octime.com/expresso/', 'https://www.octime.com/staffelio-solution-de-gestion-des-remplacements-du-personnel/', 'https://www.octime.com/nos-atouts/', 'https://www.octime.com/actualites/', 'https://www.octime.com/#minute-GTA', 'https://www.octime.com/carrieres/', 'https://www.octime.com/espace-demo/', '/mentions-legales/', '/politique-protection-donnees-personnelles/', '#', '#', '#', 'https://cookiedatabase.org/tcf/purposes/', '#', '#', '#', '#']"""