# ---- Clients
import os
import anthropic
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"

an = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))



def call_anthropic(system: str, user_content: str, temperature=0.35, max_tokens=900) -> str:
    resp = an.messages.create(
        model=ANTHROPIC_MODEL,
        system=system,
        temperature=temperature, max_tokens=max_tokens,
        messages=[{"role":"user","content":user_content}]
    )
    return "".join([b.text for b in resp.content if hasattr(b, "text")]).strip()
