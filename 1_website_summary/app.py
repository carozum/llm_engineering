# imports

import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from IPython.display import Markdown, display
from openai import OpenAI
import time
import ollama

# Pour selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Playwright - 2 commandes
# pip install playwright
# python -m playwright install
from playwright.sync_api import sync_playwright


# ###############################################################
# Set up
# ###############################################################

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
elif api_key.strip() != api_key:
    print("An API key was found, but it looks like it might have space or tab characters at the start or end - please remove them - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")
    
openai = OpenAI()


# ###################################################################
# Project with OpenAI - summarize a website
# ###################################################################

# SCRAPPER 1 - Beautiful soup pour sites statiques - simple (sans liens et images)
class Website:
    def __init__(self, url):
        self.url = url
        self.title = "Aucun titre trouvé"
        self.text = "Aucun contenu récupéré"
        self.success = False
        self.scrape()
        
    def scrape(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            self.title = soup.title.string.strip() if soup.title else "Aucun titre trouvé"
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
            self.success = True
        except Exception as e:
            self.title = "Erreur BeautifulSoup"
            self.text = f"Impossible de scraper avec BeautifulSoup: {e}"

# SCRAPPER 2 - Beautiful soup pour sites statiques - avancé avec profondeur, liens et images
class RobustWebsiteScraper:
    def __init__(self, url, max_depth=1, visited=None, user_agent=None):
        self.url = url
        self.title = None
        self.text = None
        self.links = []
        self.images = []
        self.children = []
        self.success = False
        self.error = None
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.max_depth = max_depth
        self.visited = visited if visited is not None else set()
        self.scrape(url, depth=max_depth)

    def scrape(self, url, depth):
        if url in self.visited or depth == 0:
            return
        self.visited.add(url)
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            self.title = soup.title.string.strip() if soup.title else "Aucun titre trouvé"
            # Clean main text
            for irrelevant in soup(["script", "style", "img", "input", "nav", "footer", "header"]):
                irrelevant.decompose()
            self.text = soup.get_text(separator="\n", strip=True)
            # Extract links
            base = url.rstrip('/')
            links = []
            for a in soup.find_all("a", href=True):
                href = a['href']
                if href.startswith('/'):
                    full_url = base + href
                elif href.startswith("http"):
                    full_url = href
                else:
                    continue
                if self._is_internal_link(full_url):
                    links.append({"text": a.get_text(strip=True), "url": full_url})
            self.links = links
            # Extract images
            images = []
            for img in soup.find_all("img", src=True):
                images.append({"alt": img.get("alt", ""), "src": img["src"]})
            self.images = images
            self.success = True
            # Crawl child pages if needed
            if depth > 1:
                children = []
                for link in links[:5]:  # Limite à 5 pour ne pas exploser !
                    if link["url"] not in self.visited:
                        try:
                            child = RobustWebsiteScraper(link["url"], max_depth=depth-1, visited=self.visited)
                            children.append(child)
                        except Exception as e:
                            pass
                self.children = children
        except Exception as e:
            self.title = "Erreur"
            self.text = f"Impossible de scraper: {e}"
            self.error = str(e)
            self.success = False

    def _is_internal_link(self, url):
        # Améliore cette fonction selon besoin métier
        from urllib.parse import urlparse
        return urlparse(url).netloc == urlparse(self.url).netloc

    def summary(self):
        # Récupère un résumé textuel de la page + liens + images + erreurs éventuelles
        summary = f"URL: {self.url}\nTitre: {self.title}\n\n"
        summary += f"Texte: {self.text[:500]}...\n\n"
        summary += f"Liens internes extraits: {len(self.links)}\n"
        summary += f"Images extraites: {len(self.images)}\n"
        if self.error:
            summary += f"Erreur: {self.error}\n"
        if self.children:
            summary += f"\n=== Pages enfants (niveau -1) ===\n"
            for child in self.children:
                summary += f"-> {child.url} : {child.title}\n"
        return summary


# SCRAPPER 3 - Selenium pour sites dybamiques
class WebsiteCrawler:
    def __init__(self, url):
        self.url = url
        self.title = ""
        self.text = ""
        self.success = False
        self.scrape()

    def scrape(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.get(self.url)
            time.sleep(5)
            self.title = driver.title
            page_source = driver.page_source
            driver.quit()

            soup = BeautifulSoup(page_source, 'html.parser')
            for element in soup(["script", "style", "img", "input", "button", "nav", "footer", "header"]):
                element.decompose()
            main = soup.find('main') or soup.find('article') or soup.find('body')
            if main:
                self.text = main.get_text(separator="\n", strip=True)
            else:
                self.text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in self.text.split('\n') if line.strip() and len(line.strip()) > 2]
            self.text = '\n'.join(lines[:200])
            self.success = True
        except Exception as e:
            self.title = "Erreur Selenium"
            self.text = f"Impossible de scraper avec Selenium: {e}"


# SCRAPPER 4 - playwright pour sites dynamiques

# Playwright pour JS/dynamique


class UniversalWebsiteScraper:
    """
    Classe universelle pour scraper du contenu web :
    - Utilise BeautifulSoup pour le statique
    - Bascule sur Playwright pour les sites dynamiques ou JS-only
    - Jamais d'exception non gérée
    - Résultat structuré : title, text, links, images, error
    """
    def __init__(self, url, use_playwright_if_failed=True, max_links=20):
        self.url = url
        self.title = None
        self.text = None
        self.links = []
        self.images = []
        self.success = False
        self.error = None

        # Premier essai : BeautifulSoup
        if not self._scrape_bs4():
            # Si ça échoue et option activée : Playwright
            if use_playwright_if_failed:
                self._scrape_playwright(max_links=max_links)

    def _scrape_bs4(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(self.url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            self.title = soup.title.string.strip() if soup.title else "Aucun titre trouvé"
            # Nettoyage : on vire le JS, les styles, etc.
            for tag in soup(["script", "style", "img", "input"]):
                tag.decompose()
            self.text = soup.get_text(separator="\n", strip=True)
            # Liens internes (avec netloc)
            from urllib.parse import urlparse, urljoin
            parsed_url = urlparse(self.url)
            base = f"{parsed_url.scheme}://{parsed_url.netloc}"
            self.links = []
            for a in soup.find_all("a", href=True):
                href = a['href']
                full_url = urljoin(base, href)
                if urlparse(full_url).netloc == parsed_url.netloc:
                    self.links.append(full_url)
                    if len(self.links) >= 20:
                        break
            # Images
            self.images = [img["src"] for img in soup.find_all("img", src=True)]
            self.success = True
            return True
        except Exception as e:
            self.error = f"BeautifulSoup error: {e}"
            self.success = False
            return False

    def _scrape_playwright(self, max_links=20):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.url, timeout=30000)
                page.wait_for_load_state("networkidle")
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                self.title = page.title() or "Aucun titre trouvé"
                for tag in soup(["script", "style", "img", "input"]):
                    tag.decompose()
                self.text = soup.get_text(separator="\n", strip=True)
                # Liens
                from urllib.parse import urlparse, urljoin
                parsed_url = urlparse(self.url)
                base = f"{parsed_url.scheme}://{parsed_url.netloc}"
                self.links = []
                for a in soup.find_all("a", href=True):
                    href = a['href']
                    full_url = urljoin(base, href)
                    if urlparse(full_url).netloc == parsed_url.netloc:
                        self.links.append(full_url)
                        if len(self.links) >= max_links:
                            break
                # Images
                self.images = [img["src"] for img in soup.find_all("img", src=True)]
                browser.close()
                self.success = True
                self.error = None
        except Exception as e:
            self.title = "Erreur Playwright"
            self.text = f"Impossible de scraper avec Playwright: {e}"
            self.error = f"Playwright error: {e}"
            self.success = False

    def summary(self):
        summary = f"URL: {self.url}\nTitre: {self.title}\n\n"
        summary += f"Texte: {self.text[:500]}...\n\n"
        summary += f"Liens internes extraits: {len(self.links)}\n"
        summary += f"Images extraites: {len(self.images)}\n"
        if self.error:
            summary += f"Erreur: {self.error}\n"
        return summary

# --------------------------------------------------------------
# Fonction de wrapper pour scraper proprement :
def get_website_content(url):
    site = UniversalWebsiteScraper(url)
    # print(site.summary())
    return site


# Fonction consolidée d'accès (fallback)
# def get_website_content(url):
#     # D'abord BeautifulSoup
#     # site = Website(url)
#     site = RobustWebsiteScraper(url, max_depth=1)
#     # print(site.success)
#     if site.success:
#         print(site.title)
#         print(site.summary())
#         # Pour afficher les liens :
#         for l in site.links:
#             print(l)
#         # Pour afficher les images :
#         for img in site.images:
#             print(img)
#         return site
#     # Sinon Selenium
#     site = WebsiteCrawler(url)
#     return site



# ###############################################################
# calling LLM
# ###############################################################

# Define a system prompt 

system_prompt = "You are an assistant that analyzes the contents of a website \
and provides a short summary, ignoring text that might be navigation related. \
Respond in markdown in French."

# A function that writes a User Prompt that asks for summaries of websites:

def user_prompt_for(website):
    user_prompt = f"You are looking at a website titled {website.title}"
    user_prompt += "\nThe contents of this website is as follows; \
please provide a short summary of this website in markdown. \
If it includes news or announcements, then summarize these too.\n\n"
    user_prompt += website.text
    return user_prompt
# print(user_prompt_for(url))

# See how this function creates exactly the format above

def messages_for(website):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(website)}
    ]
# Calling OpenAI with system and user messages:

def summarize_openai(url):
    website = get_website_content(url) 
    response = openai.chat.completions.create(
        model = "gpt-4o-mini",
        # model = "phi3",
        messages = messages_for(website)
    )
    return response.choices[0].message.content


def summarize_ollama(url):
    website = get_website_content(url) 
    # PREMIERE METHODE EN UTILISANT OPENAI
    # openai = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
    # response = openai.chat.completions.create(
    #     # model = "gpt-4o-mini",
    #     model = "phi3",
    #     messages = messages_for(website)
    # )
    
    # DEUXIEME METHODE PAR REQUEST
    # payload = {
    #         "model": "phi3",
    #         "messages": messages_for(website),
    #         "stream": False
    #     }
    # response = requests.post(
    #     "http://localhost:11434/api/chat",
    #     json=payload
    # )
    # # print(response.json()["message"]["content"])
    # answer = response.json()["message"]["content"]
    
    # TROISIEME METHODE EN UTILISANT LE MODULE OLLAMA
    response = ollama.chat(model="phi3", messages = messages_for(website))
    answer = response["message"]["content"]
    
    return answer




# --------------------------------------------------------------
# Exemple d'utilisation :

# url = "https://octime.com"
# url = "https://learn.microsoft.com/en-us/training/modules/ai-agent-fundamentals/"
# url="https://unsplash.com/fr/@carozum"
# url="https://www.linkedin.com/company/groupeoctime/"
# url="https://twitter.com/GroupeOctime"
url="https://www.facebook.com/groupeoctime"
site = get_website_content(url)
print("website title", site.title)
print()
print(summarize_openai(url))
# print()
# print("==========================================")
# print(summarize_ollama(url))
# print(summarize("https://cnn.com"))
# print(summarize("https://anthropic.com"))

"""
Réponse de OpenAI GPT4o mini
# Résumé du site Logiciel RH

Le site présente **OCTIME**, un logiciel de gestion des ressources humaines conçu pour optimiser la planification, le suivi des temps de travail, la gestion des congés et des absences. Le Groupe Octime propose des solutions modulaires adaptées à diverses structures, allant des TPE/PME aux grandes entreprises, permettant une amélioration notable de l’efficacité organisationnelle.

## Caractéristiques principales :

- **Gestion des temps et activités** : Automatisation du suivi des heures, absences, et activités des employés pour améliorer la performance.
- **Gestion des plannings** : Création de plannings flexibles en fonction des besoins opérationnels et des réglementations.   
- **Gestion des absences** : Processus optimisé pour la gestion des absences, réduisant ainsi les coûts liés à l’absentéisme. 
- **Logiciel de pointage** : Outils pour contrôler les horaires de travail, garantissant la fiabilité des données.

## Innovations et services :

- **Expertise R&D** : Un laboratoire d'innovation dédié aux technologies de gestion des temps.
- **Support client** : Accès à une équipe d’experts pour l’accompagnement et la formation.
- **Communauté d’utilisateurs** : Plus de 1,6 million d’utilisateurs, avec des solutions déployées dans 15 500 sites en France.

## Actualités :

- **La Minute GTA** : Une newsletter mensuelle fournissant des actualités, témoignages et expertises autour de la gestion des temps et des plannings.

Le site souligne l’importance d’un accompagnement personnalisé tout au long du projet pour assurer la réussite dans l’optimisation de la gestion des ressources humaines.

=========================================================================
Réponse de Ollama Phi3

# Summary of the website content in French:

Le Groupe Octime propose une gamme complète de solutions RH pour optimiser la gestion des ressources humaines, qui s'adresse à tous types d'organisations. Leur logiciel OCTIME est conçu avec l'objectif d'améliorer les opérations organisationnelles grâce au suivi automatisé et sécurisé de horaires, absences, congés et activités des employés, tout en simplifiant la vie pour les managers et les salariés.

Les services proposent une gestion modulaire avec adaptabilité à tous métiers et réglementations spécifiques. OCTIME Expresso est spécialisé dans le planning pour TPE/PME grâce à un système unique sur marché qui met en place des horaires de travail facilement et automatisés, tenant compte des besoins personnels ou opérationnels tout en respectant les ententes réglementaires. 

La gestion du temps est simplifiée avec OCTIME pour faciliter la création de plannings adaptés aux organisations publiques et privées dans tous domaines d'activité, tels que des réajustements saisonniers, recrutement ou formation. De plus, l'OCTIME permet une prise en compte rapide des variations horaires pour améliorer la réactivité de votre organisation grâce à un planning digitalisé et automatisé.

La gestion des absences est optimisée via OCTIME permettant d'automatiser le suivi des demandes, augmentant ainsi l'efficacité face au gaspillage lié aux horaires non-conformes ou manqués du personnel (congés payés, RTT, congés maternités...).

Le logiciel de pointage automatise le transfert des informations des heures et garantit la fiabilité des temps de travail. Les badgeuses pointeuses synchronisées avec OCTIME permettent un contrôle efficace du temps de travail respectant les horaires prévus pour chaque collaborateur, ce qui assure une conformité fiscale optimisée.

Le Groupe Octime propose également des solutions d'éducation et formation personnalisée par l’intermédiaire de son équipe expérimentée dans le secteur RH avec un support client réactif pour répondre rapidement aux besoins spécifiques du projet. Leur approche continue, en favorisant les synergies au sein même entre entreprises historiques et émergentes d'OCTIME comme aTurnos et Staffelio by OCTIME, témoigne de leur engagement à offrir une solution unique avec des technologies modulables pour différents secteurs.

La stratégie en détail du Groupe Octime comprend un accompagnement expertisé aux besoins spécifiques d'une organisation et les programmes clairs pour le soutien continu, la formation et l'expertise légale RH qui s'ajustent à différents secteurs avec des références reconnues.

Enfin, OCTIME encourage une bonne expérience client par rapport au service support en ligne accessible toute heure de la journée pour répondre aux besoins et demandes d’utilisateurs quotidiens. La Minute GTA est leur initiative permettant à des utilisateurs inscrits régulièrement recevoir des informations clés sur les mises à jour, événements et actualités en RH sans se soucier de vérifier fréquemment le site web pour la dernière information disponible, améliorant ainsi l'expérience client.

Note: The text includes mentions of a login requirement for the Minute GTA newsletter and cookie policy details which are not translated into French but should be conveyed accurately to ensure compliance with privacy regulations in France (e.g., RGPD).
# Summary of the website content in French:

Le Groupe Octime propose une gamme complète de solutions RH pour optimiser la gestion des ressources humaines, qui s'adresse à tous types d'organisations. Leur logiciel OCTIME est conçu avec l'objectif d'améliorer les opérations organisationnelles grâce au suivi automatisé et sécurisé de horaires, absences, congés et activités des employés, tout en simplifiant la vie pour les managers et les salariés.

Les services proposent une gestion modulaire avec adaptabilité à tous métiers et réglementations spécifiques. OCTIME Expresso est spécialisé dans le planning pour TPE/PME grâce à un système unique sur marché qui met en place des horaires de travail facilement et automatisés, tenant compte des besoins personnels ou opérationnels tout en respectant les ententes réglementaires. 

La gestion du temps est simplifiée avec OCTIME pour faciliter la création de plannings adaptés aux organisations publiques et privées dans tous domaines d'activité, tels que des réajustements saisonniers, recrutement ou formation. De plus, l'OCTIME permet une prise en compte rapide des variations horaires pour améliorer la réactivité de votre organisation grâce à un planning digitalisé et automatisé.

La gestion des absences est optimisée via OCTIME permettant d'automatiser le suivi des demandes, augmentant ainsi l'efficacité face au gaspillage lié aux horaires non-conformes ou manqués du personnel (congés payés, RTT, congés maternités...).

Le logiciel de pointage automatise le transfert des informations des heures et garantit la fiabilité des temps de travail. Les badgeuses pointeuses synchronisées avec OCTIME permettent un contrôle efficace du temps de travail respectant les horaires prévus pour chaque collaborateur, ce qui assure une conformité fiscale optimisée.

Le Groupe Octime propose également des solutions d'éducation et formation personnalisée par l’intermédiaire de son équipe expérimentée dans le secteur RH avec un support client réactif pour répondre rapidement aux besoins spécifiques du projet. Leur approche continue, en favorisant les synergies au sein même entre entreprises historiques et émergentes d'OCTIME comme aTurnos et Staffelio by OCTIME, témoigne de leur engagement à offrir une solution unique avec des technologies modulables pour différents secteurs.

La stratégie en détail du Groupe Octime comprend un accompagnement expertisé aux besoins spécifiques d'une organisation et les programmes clairs pour le soutien continu, la formation et l'expertise légale RH qui s'ajustent à différents secteurs avec des références reconnues.

Enfin, OCTIME encourage une bonne expérience client par rapport au service support en ligne accessible toute heure de la journée pour répondre aux besoins et demandes d’utilisateurs quotidiens. La Minute GTA est leur initiative permettant à des utilisateurs inscrits régulièrement recevoir des informations clés sur les mises à jour, événements et actualités en RH sans se soucier de vérifier fréquemment le site web pour la dernière information disponible, améliorant ainsi l'expérience client.

Note: The text includes mentions of a login requirement for the Minute GTA newsletter and cookie policy details which are not translated into French but should be conveyed accurately to ensure compliance with privacy regulations in France (e.g., RGPD).
"""