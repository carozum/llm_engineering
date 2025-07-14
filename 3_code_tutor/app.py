# imports


# constants

MODEL_GPT = 'gpt-4o-mini'
MODEL_LLAMA = 'llama3.2'


# set up environment


# here is the question; type over this to ask something new
code = """
yield from {book.get("author") for book in books if book.get("author")}
"""

question = f"""
Please explain what this code does and why:
{code}
"""

# gpt-4o-mini to answer, with streaming


# Get Llama 3.2 to answer