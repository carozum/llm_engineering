from typing import List, Dict
import os
from dotenv import load_dotenv
load_dotenv()

def call_gemini(messages: List[Dict], model="gemini-2.5-pro") -> str:
    import google.generativeai as genai
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        return "⚠️ GOOGLE_API_KEY manquant."
    genai.configure(api_key=key)

    # On concatène system + historique en un prompt pour simplicité (MVP)
    system = "\n".join([m["content"] for m in messages if m["role"]=="system"])
    convo = []
    for m in messages:
        if m["role"] == "user":
            convo.append(f"User: {m['content']}")
        elif m["role"] == "assistant":
            convo.append(f"Assistant: {m['content']}")
    prompt = (system + "\n\n" if system else "") + "\n".join(convo) + "\nAssistant:"
    model = genai.GenerativeModel(model)
    resp = model.generate_content(prompt)
    return resp.text