import os, time
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# --- Providers ---------------------------------------------------------------

from call_anthropic import call_anthropic
from call_openai import call_openai
from call_gemini import call_gemini

# --- upload et rag -----------------------------------------------------------

from utils_upload import load_index, save_index, delete_document
from utils_rag import index_file_to_chroma, rag_query, build_system_prompt, describe_image_with_llm
import uuid, pathlib
DATA_DIR = pathlib.Path("data_uploads")

# --- Router ------------------------------------------------------------------
def call_model(provider: str, messages: List[Dict]) -> str:
    if provider == "openai":
        return call_openai(messages)
    if provider == "anthropic":
        return call_anthropic(messages)
    if provider == "gemini":
        return call_gemini(messages)
    return "⚠️ Provider inconnu."

# --- UI ----------------------------------------------------------------------
st.set_page_config(page_title="Mentor – MVP", page_icon="🧠", layout="centered")
st.title("🧠 Mentor – MVP (multiturn + choix modèle)")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "provider" not in st.session_state:
    st.session_state.provider = os.getenv("DEFAULT_MODEL_PROVIDER", "anthropic")

st.sidebar.header("Paramètres")
provider = st.sidebar.selectbox("Fournisseur", ["anthropic","openai","gemini"], index=["anthropic","openai","gemini"].index(st.session_state.provider))
st.session_state.provider = provider

if st.sidebar.button("🗑️ Réinitialiser la conversation"):
    st.session_state.messages = []
    st.rerun()
    
# --- Upload -------------------------------------------------------------------

st.sidebar.subheader("📎 Upload de documents")
subject = st.sidebar.selectbox("Sujet", ["maths","physique", "chimie", "programmation"], index=0)
year = st.sidebar.text_input("Année/Niveau", "2025/26")
chapters = st.sidebar.text_input("Chapitres (CSV)", "")

file = st.sidebar.file_uploader("PDF / Image", type=["pdf","png","jpg","jpeg"])
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
    
    # if entry["kind"] == "image":
    #     texte = describe_image_with_llm(entry)


with st.sidebar.expander("📚 Mes documents", expanded=False):
    idx = load_index()
    if not idx:
        st.caption("Aucun document.")
    else:
        for it in idx[::-1]:
            cols = st.columns([1.7, 1, 0.6])
            with cols[0]:
                st.write(f"**{it['name']}**")
                st.caption(f"{it['subject']} / {it['year']} / {', '.join(it['chapters']) or '–'}")
            # with cols[1]:
            #     st.caption(f"ID: {it['id'][:8]}…")
            with cols[2]:
                if st.button("🗑️", key=f"del-{it['id']}"):
                    delete_document(it["id"])
                    st.success(f"Supprimé : {it['name']}")
                    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔁 Réindexer tous les PDFs"):
    idx = load_index()
    ok, ko = 0, 0
    for it in idx:
        if it.get("kind") == "pdf":
            try:
                index_file_to_chroma(it)  # prendra la nouvelle version (chapters_csv)
                ok += 1
            except Exception as e:
                ko += 1
    st.sidebar.success(f"Réindexation terminée. OK={ok}, erreurs={ko}")


# --- RAG san sidebar-------------------------------------------------------------------------------------
st.sidebar.subheader("🔎 RAG (recherche contextuelle)")
use_rag = st.sidebar.checkbox("Activer le RAG", value=True)
k = st.sidebar.slider("Top-k", min_value=2, max_value=10, value=5)
subject_filter = st.sidebar.selectbox("Filtrer Sujet (optionnel)", ["(auto)", "maths","physique", "chimie", "programmation"], index=0)
year_filter = st.sidebar.text_input("Filtrer Année (optionnel)", "")
chapters_filter = st.sidebar.text_input("Filtrer Chapitres (CSV, optionnel)", "")

            

# --- Chat multiturn UI + sauvegarde-----------------------------------------------------------
for m in st.session_state.messages:
    if m["role"] in ("user","assistant"):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            
BASE_SYSTEM = "Tu es un tuteur bienveillant. Sois clair, étape par étape. Cite tes sources si contexte."

user_input = st.chat_input("Pose ta question…")
if user_input:
    
    # ajouter le tour  user à l'historique
    st.session_state.messages.append({"role":"user","content":user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # === RAG ===
    rag_snippets = []
    if use_rag:
        subj = None if subject_filter == "(auto)" else subject_filter
        yearf = year_filter.strip() or None
        chaps = [c.strip() for c in chapters_filter.split(",") if c.strip()] or None
        try:
            rag_snippets = rag_query(user_input, k=k, subject=subj, year=yearf, chapters=chaps)
        except Exception as e:
            st.sidebar.warning(f"RAG indisponible: {e}")

    # Construire les messages à envoyer AU MODELE pour CE tour uniquement
    system_for_turn = {
        "role": "system",
        "content": build_system_prompt(BASE_SYSTEM, rag_snippets) if use_rag else BASE_SYSTEM
    }
    msgs = [system_for_turn, *st.session_state.messages] 
    
    
    with st.chat_message("assistant"):
        with st.spinner("Réflexion…"):
            try:
                answer = call_model(st.session_state.provider, msgs)
            except Exception as e:
                answer = f"❌ Erreur: {e}"
            # Afficher éventuellement les sources
            # if rag_snippets:
            #     st.caption("Sources:")
            #     for h in rag_snippets:
            #         src = h["meta"].get("source","doc")
            #         chunk = h["meta"].get("chunk",0)
            #         st.caption(f"• {src} (chunk {chunk})")
            if rag_snippets:
                with st.expander("📚 Sources utilisées", expanded=False):
                    for j, h in enumerate(rag_snippets, 1):
                        meta = h["meta"]
                        src = meta.get("source","doc")
                        ps, pe = meta.get("page_start"), meta.get("page_end")
                        st.markdown(f"**[{j}] {src}** — pages {ps}–{pe} (chunk {meta.get('chunk',0)})")
                        preview = (h.get("text") or "").strip()
                        # st.code(preview[:600] + ("…" if len(preview)>600 else ""), language="text")
                        # bouton download
                        path = next((it["path"] for it in load_index() if it["name"]==src), None)
                        if path and pathlib.Path(path).exists():
                            with open(path, "rb") as f:
                                st.download_button("Télécharger le PDF", f, file_name=src, key=f"dl-{src}-{j}")

            st.markdown(answer)
    st.session_state.messages.append({"role":"assistant","content":answer})
