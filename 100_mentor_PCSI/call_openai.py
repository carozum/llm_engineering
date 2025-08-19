from typing import List, Dict
import os
from dotenv import load_dotenv
load_dotenv()


def call_openai(messages: List[Dict], model="gpt-4o-mini") -> str:
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "⚠️ OPENAI_API_KEY manquant."
    client = OpenAI(api_key=key)
    # messages -> format OpenAI {role, content}
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=800
    )
    return resp.choices[0].message.content