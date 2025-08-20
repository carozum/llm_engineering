import os
from dotenv import load_dotenv
from typing import List, Dict
from openai import OpenAI
load_dotenv(override=True)

deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')

def call_deepseek(messages: List[Dict], model="deepseek-chat") -> str:
    # Using DeepSeek Chat

    deepseek_via_openai_client = OpenAI(
        api_key=deepseek_api_key, 
        base_url="https://api.deepseek.com"
    )

    response = deepseek_via_openai_client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content