import os
# ---- Clients
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

OPENAI_MODEL = "gpt-4.1"        
oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_openai(system: str, user_content: str, temperature=0.35, max_tokens=900) -> str:
    resp = oa.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user_content}],
        temperature=temperature, max_tokens=max_tokens
    )
    return resp.choices[0].message.content.strip()
