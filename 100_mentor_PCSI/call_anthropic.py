from typing import List, Dict
import os
from dotenv import load_dotenv
load_dotenv()


def call_anthropic(messages: List[Dict], model="claude-3-5-sonnet-20240620") -> str:
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return "⚠️ ANTHROPIC_API_KEY manquant."
    client = anthropic.Client(api_key=key)

    # Convertir messages OpenAI-like vers Anthropic:
    system = ""
    content = []
    for m in messages:
        if m["role"] == "system":
            system += m["content"] + "\n"
        elif m["role"] in ("user", "assistant"):
            content.append({"role": m["role"], "content": m["content"]})

    resp = client.messages.create(
        model=model,
        # max_tokens=800,
        temperature=0.2,
        system=system or None,
        messages=content
    )
    # Concat text parts
    return "".join(b.text for b in resp.content if b.type == "text")