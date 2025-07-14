# scraping d'un site et résumé de ce site

Extraction dans le cas de sites statiques par Beautiful soup
Extraction dans le cas de sites dynamiques par Sélénium (en particulier pour les sites qui demandent une authentification --> blocage à la page de connexion mais pas de crash)
Extraction titre, texte, image et lien
Possibilité d'augmenter la profondeur de crawl

Résumé du contenu de ce site 
- en utilisant OpenAI gpt4o mini
- en utilisant Ollama : pour cela 
        - télécharger Ollama en local
        - lancer le serveur d'inférence ollama en faisant : ollama serve. Cela démarre le service d’inférence sur localhost:11434
        - charger un modèle : ollama pull phi3 (3.8B), ollama pull llama3 (8B), ollama pull mistral (7B)
        - tester dans le terminal en local : ollama run phi3
        - dans le script : appel via openai = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
        ```
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "phi3", "prompt": "Résume-moi le RGPD en français.", "stream": False}
            )
            print(response.json()["response"])
        ```

Rendu en markdown

Dans le cas d'un site dynamique, possibilité d'utiliser **playwright**. 


# requirements : 

requests
python-dotenv
bs4
IPython
openai
selenium
webdriver-manager
playwight
ollama

# .env
OPENAI_API_KEY= à compléter
