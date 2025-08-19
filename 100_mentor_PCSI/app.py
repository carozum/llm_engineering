import os, time
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# --- Providers ---------------------------------------------------------------

from call_anthropic import call_anthropic
from call_openai import call_openai
from call_gemini import call_gemini


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
    st.session_state.messages = [{"role":"system","content":"Tu es un tuteur bienveillant. Sois clair, étape par étape."}]
if "provider" not in st.session_state:
    st.session_state.provider = os.getenv("DEFAULT_MODEL_PROVIDER", "anthropic")

st.sidebar.header("Paramètres")
provider = st.sidebar.selectbox("Fournisseur", ["anthropic","openai","gemini"], index=["anthropic","openai","gemini"].index(st.session_state.provider))
st.session_state.provider = provider

if st.sidebar.button("🗑️ Réinitialiser la conversation"):
    st.session_state.messages = [{"role":"system","content":"Tu es un tuteur bienveillant. Sois clair, étape par étape."}]
    st.rerun()

# Render historique (sans le system)
for m in st.session_state.messages:
    if m["role"] in ("user","assistant"):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

user_input = st.chat_input("Pose ta question…")
if user_input:
    st.session_state.messages.append({"role":"user","content":user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Réflexion…"):
            try:
                answer = call_model(st.session_state.provider, st.session_state.messages)
            except Exception as e:
                answer = f"❌ Erreur: {e}"
            st.markdown(answer)
    st.session_state.messages.append({"role":"assistant","content":answer})
