# MVP Mentor Prépa PC

✅ Une collection globale + métadonnées riches (subject, year, chapters).

✅ Recherche en cascade : avec filtres.

✅ UI claire : Sélecteur de sujet/année/chapitres + visibilité à l’upload.

✅ Extensible : facile de transférer à un “utilisateur économie” demain, sans casser le reste.

## Technos
Streamlit --> bootstrap, python, Chroma --> QDrant, SQLite3 --> postGres

| Option                              | Quand l’utiliser                                | Avantages                                           | Limites                                                              |
| ----------------------------------- | ----------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------- |
| **Streamlit**                       | Prototyper très vite, local, un seul fichier    | Ultra-rapide, composant chat natif, state simple    | Moins flexible pour une UX très custom / multi-pages “produit” |
| **Gradio**                          | Démos IA simples, notebooks                     | Upload/preview simples, hosting facile (Spaces)     | UX moins “app”, styling limité                                       |
| **FastAPI + Jinja2/HTMX/Bootstrap** | **Produit long terme**, contrôle fin, auth, SEO | Total contrôle, propre en prod, facile à dockeriser | Demande plus de code (forms, state, websockets si live stream)       |



## Modèles 
- OpenAI
- Antrhopic
- Gemini

==> TODO Ajouter Deepseek

## Lancer

pip install -r requirements.txt

streamlit run app.py


## Feuille de route

✅ MVP 1 --- Streamlit (ci-dessus) : multiturn + choix modèle.

    ➕ ajouter deepSeek comme modèle

    ➕ Multi-modèles par sujet : p.ex. maths/physique → modèle de raisonnement fort ; éco/droit → modèle plus verbeux/structuré (références, définitions). On peut router par subject côté code (sélection du model=).

✅ MVP 1.1 Upload + tags (ci-dessus).
==> TODO ajouter d'autres types de documents docx...

✅ MVP 1.2 Possibilité de supprimer des documents uploadés

➕  RAG : 

    ✅ avec ChromaDB et possibilité de choisir si utilisé ou pas

    ==> indexation des images ? par génération d'un texte descriptif

    ==> service QDRANT pour remplacer Chroma ?
        Chroma (MVP) : OK, gère where sur metadata → parfait pour démarrere et pouvoir filtrer.
        Qdrant (niveau 2) : filtres payload puissants, perf et scale meilleurs.
        
        Qdrant : qu’est-ce que ça apporte vs Chroma ?
        En bref : Qdrant = moteur vecteur serveur (hautement fiable + filtres puissants), Chroma = lib Python pratique (MVP local).
        Avantages Qdrant concrets :
        - Filtres/Payloads puissants : must/should/must_not, filtres sur listes (overlap), range, bool, etc.
        - Index de payload (accélère les filtres), snapshots & backups natifs.
        - Multi-collections, named vectors (plusieurs embeddings par doc : denses/sparses/hybrides).
        - Perf & scale : HNSW optimisé, quantization (SQ, PQ), shard/replica en édition distribuée.
        - APIs REST/gRPC + clients officiels (Python/JS/Rust), intégration facile en prod (Docker/K8s).
        - Hybrid search (BM25+sparse+dense) avec les features récentes.

        👉 Si on veut multi-utilisateurs, multi-sujets avec filtres (subject, year, chapters, visibility, owner), Qdrant est nettement plus robuste.

    ==> pdf pas de lecture des images ?

    ==> visualisation des sources 

    ==> reranker open-source: Cohere Rerank, bge-reranker, ou un petit cross-encoder local

➕ Vision (photo d’énoncés) : ajoute vision_parse() (Claude/GPT/Gemini).
    OCR de formules : si jamais la vision LLM patine, ajoute Mathpix pour LaTeX robuste.

➕ Agents : LangGraph dans le backend FastAPI (router → retrieve → solve → critic). fichier graph.py (LangGraph minimal)
    LangGraph pour l’orchestration multi-agents :
    - RouterAgent (détecte le sujet + mode),
    - TutorAgent (Socratique / solution),
    - outils : retrieve(), vision_parse(), sympy_solve(), unit_check(), critic().

➕ Authentification ou déployer des images différentes pour les différents utilisateur (version assistant personnel)

➕ Passer à des routes / microservices FASTAPI, me le conseille tu ? pour le moment, monolithique. 

➕ Est ce que Streamlit peut être utilisé en prod ?? assez fiable ??

➕ anki : export .csv (Question;Réponse;Tag) depuis les échanges taggés “À réviser”.

➕ garder la trace des erreurs courantes

➕ Sauvegarde des fichiers sur un cloud

➕ Uploader directement dans la question sans que çà entre dans le RAG

➕ personnalisation utilisateur (résumé d'une conversation) -- où sauvegarder ? 
    Mémoire “profil” (préférences & lacunes) : table user_profiles + injection dans le prompt système à chaque tour + user_stats.
    Crée une table user_profiles et mets un middleware qui injecte un résumé dans le system prompt à chaque tour.
   
    Où enregistrer “ce que l’utilisateur aime” ?
    - Profil (préférences explicites : format, mode, rythme).
    - Historique agrégé (tags rencontrés + erreurs fréquentes).
    - Exemple : table user_stats(user_id, tag, seen_count, error_count, last_seen_at) mise à jour après chaque tour.
    - Ça alimente :
        - un pré-prompt (rappeler méthodes adaptées),
        - un plan de révision (générer des cartes Anki ciblées).

    Auto-mise à jour : après chaque tour, tagge les sujets détectés (LLM ou simple regex sur la réponse) et incrémente les compteurs d’erreurs récurrentes (ex. signe, dérivation produit, unités).
    

➕ Voir les conversations anciennes. DB Postgres ou SQLite3 ?

➕ Back Fast API : un /retrieve, un /chat... main.py complet (endpoints /chat, /upload, /docs)

    FastAPI pour exposer :
    - POST /chat (multimodal, multi-provider),
    - POST /upload (stockage + metadata),
    - GET /docs (liste filtrée),
    - POST /retrieve (RAG).

    backend/
        main.py              # FastAPI (endpoints)
        graph.py             # LangGraph (route -> retrieve -> solve -> critic)
        llm_clients.py       # OpenAI/Anthropic/Gemini wrappers
        storage/
            uploads/           # fichiers
            index.db           # SQLite (docs, tags, users)
        rag/
            qdrant_adapter.py  # plus tard


➕ en prod
    ==> VM : Docker + Caddy (HTTPS) — tu auras déjà la séparation front/back.
    ==> plus un docker-compose prêt pour la VM.



-------------------------------------------------------------------------------------------------------------------------------------------------

# Version “Agent” : qu’est-ce qui change ?

## 1) Architecture recommandée

Un **RouterAgent** (détermine le sujet + le mode : socratique vs solution, “avec RAG” vs “pur raisonnement”).

Des **Outils** (plutôt que “un agent par matière” rigide) :
- retrieve(subject, year, chapters) → interroge le vector store (Chroma/Qdrant).
- vision_parse() → lit une photo/scan et renvoie LaTeX + texte structuré.
- math_solve() → essai SymPy pour calculs symboliques (intégrales, dérivées, systèmes).
- unit_check() → vérifie cohérence d’unités.
- critic() → relit la solution et signale erreurs/omissions.

Un **TutorAgent** (LLM) qui planifie : comprendre → décomposer → appeler les outils → expliquer → vérifier → citer.

Pourquoi pas “un agent par matière” ?
Possible, mais en pratique un router + un tuteur unique avec des outils spécialisés est plus simple à maintenir et réutiliser. Si un jour l’économie/droit nécessitent des règles vraiment différentes, tu ajoutes un SubjectPolicyAgent (politiques par matière) que le Router appelle.

## 2) Squelette minimal avec LangGraph (idée)

```
# pip install langgraph langchain openai qdrant-client sympy
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any

class S(TypedDict):
    query: str
    subject: str
    context: List[Dict]   # passages RAG
    plan: str
    answer: str

def route_subject(s: S) -> str:
    # soit lire le dropdown UI, soit classer via LLM
    return "retrieve" if s["subject"] in {"maths","physique","economie","droit"} else "solve"

def retrieve_node(s: S) -> S:
    s["context"] = retrieve(subject=s["subject"], query=s["query"])  # ton wrapper
    s["plan"] = "décomposer en étapes avec sources"
    return s

def solve_node(s: S) -> S:
    s["answer"] = tutor_llm(query=s["query"], context=s["context"])  # ton prompt système socratique
    return s

def critic_node(s: S) -> S:
    s["answer"] = critic_llm(s["answer"])  # contrôle cohérence + unités + citations
    return s

g = StateGraph(S)
g.add_node("retrieve", retrieve_node)
g.add_node("solve", solve_node)
g.add_node("critic", critic_node)
g.add_edge(START, route_subject)
g.add_edge("retrieve", "solve")
g.add_edge("solve", "critic")
g.add_edge("critic", END)
app = g.compile()
```

Bénéfices : traçabilité des étapes, facile d’insérer un vision_parse ou un math_solve(sympy) à un endroit précis.










QUESTIONS POUR GPT


if st.sidebar.button("Uploader") and file is not None:
    fid = uuid.uuid4().hex
    ext = pathlib.Path(file.name).suffix.lower()
    out = DATA_DIR / f"{fid}{ext}"
    out.write_bytes(file.read())
    entry = {
        "id": fid,
        "name": file.name,
        "path": str(out),
        "subject": subject,
        "year": year,
        "chapters": [c.strip() for c in chapters.split(",") if c.strip()],
        "kind": "pdf" if ext==".pdf" else "image"
    }
    idx = load_index()
    idx.append(entry)
    save_index(idx)
    st.sidebar.success(f"Fichier enregistré : {file.name}")

    # Indexation RAG si PDF
    if entry["kind"] == "pdf":
        try:
            index_file_to_chroma(entry)
            st.sidebar.info("Indexé dans le moteur de recherche (RAG).")
        except Exception as e:
            st.sidebar.warning(f"Indexation partielle: {e}")
    
    if entry["kind"] == "image":
        texte = describe_image_with_llm(entry)

COmment j'adapte pour l'image ? À l’upload, si kind == "image", tu appelles  describe_image_with_llm, puis tu fais un col.add avec le texte et des métadonnées (page_start/page_end peuvent être None).

--------------------------------------------------------------------------------------------------------------------------

(c) Vision (photo d’énoncé)
Ajoute un bouton “Analyser une image” : on reformule en texte + LaTeX + on propose une stratégie. Tu as déjà la fonction describe_image_with_llm.

Tu peux décrire. 

----------------------------------------------------------------------------------------------

(d) Agents (LangGraph) + FastAPI
Oui, je te conseille de garder Streamlit pour l’UI mais d’extraire la logique vers un backend FastAPI quand tu ajoutes les agents et Qdrant.

LangGraph = orchestration claire : route → retrieve → solve → critic.

Tu pourras appeler /chat depuis Streamlit.

Si tu veux, je te file un graph.py minimal + main.py FastAPI au prochain pas — mais tu as déjà beaucoup ici, restons focus.