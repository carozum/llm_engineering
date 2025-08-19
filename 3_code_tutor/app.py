# imports
from dotenv import load_dotenv
from IPython.display import Markdown, display, update_display
from openai import OpenAI
import ollama

# constants

MODEL_GPT = 'gpt-4o-mini'
MODEL_LLAMA = 'llama3.2'


# set up environment

load_dotenv()
openai = OpenAI()


# here is the question; type over this to ask something new

code = input("Please enter your code extract:")
# code = """
# yield from {book.get("author") for book in books if book.get("author")}
# """

question = f"""
Please explain what this code does and why:
{code}
"""

# prompts

system_prompt = "You are a helpful technical tutor who answers questions about python code, software engineering, data science and LLMs"

user_prompt = "Please give a detailed explanation to the following question: " + question

# messages

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]

# Get gpt-4o-mini to answer, with streaming
def stream_brochure_chunks(user_prompt):
    """
    Generator qui stream les morceaux de texte renvoyés par l'API OpenAI.
    """
    stream = openai.chat.completions.create(
        model=MODEL_GPT, 
        messages=messages,
        stream=True)
    
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ''
        if delta:
            yield delta

for token in stream_brochure_chunks(user_prompt):
    print(token, end='', flush=True)


# Get Llama 3.2 to answer
# ollama pull llama3:8b

# response = ollama.chat(model=MODEL_LLAMA, messages=messages)
# reply = response['message']['content']
# print(reply)



# yield from {book.get("author") for book in books if book.get("author")}
