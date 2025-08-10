
# A full business solution :
# Create a product that builds a Brochure for a company to be used for prospective clients, investors and potential recruits.
# We will be provided a company name and their primary website.


# imports
# If these fail, please check you're running from an 'activated' environment with (llms) in the command prompt

import os
import requests
import json
from typing import List
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from openai import OpenAI

# ############################################################################
# Initialize and constants

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if api_key and api_key.startswith('sk-proj-') and len(api_key)>10:
    print("API key looks good so far")
else:
    print("There might be a problem with your API key? Please visit the troubleshooting notebook!")
    
MODEL = 'gpt-4o-mini'
openai = OpenAI()

# ############################################################################
# A class to represent a Webpage

# Some websites need you to use proper headers when fetching them:
headers = {
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

class Website:
    """
    A utility class to represent a Website that we have scraped, now with links
    """

    def __init__(self, url):
        self.url = url
        
        response = requests.get(url, headers=headers)
        self.body = response.content
        
        soup = BeautifulSoup(self.body, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"
        
        if soup.body:
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""
        links = [link.get('href') for link in soup.find_all('a')]
        self.links = [link for link in links if link]

    def get_contents(self):
        return f"Webpage Title:\n{self.title}\nWebpage Contents:\n{self.text}\n\n"
    
oct = Website("https://www.octime.com")
# print(oct.links)

# ############################################################################
# First step: Have GPT-4o-mini figure out which links are relevant relative to our use case
# ############################################################################

# Use a call to gpt-4o-mini to read the links on a webpage, and respond in structured JSON.
# It should decide which links are relevant, and replace relative links such as "/about" with "https://company.com/about".
# We will use "one shot prompting" in which we provide an example of how it should respond in the prompt.

# We could have used a more advanced technique called "Structured Outputs" in which we require the model to respond according to a spec.

##################### PROMPT ORIENTE BROCHURE MARKETING
# link_system_prompt = "You are provided with a list of links found on a webpage. \
# You are able to decide which of the links would be most relevant to include in a brochure about the company, \
# such as links to an About page, or a Company page, or Careers/Jobs pages.\n"
# link_system_prompt += "You should respond in JSON as in this example:"
# link_system_prompt += """
# {
#     "links": [
#         {"type": "about page", "url": "https://full.url/goes/here/about"},
#         {"type": "careers page", "url": "https://another.full.url/careers"}
#     ]
# }
# """
# print(link_system_prompt)

##################### PROMPT ORIENTE BROCHURE FINANCIERS
link_system_prompt = """
You are provided with a list of links found on a company's website.
Your goal is to identify pages that are most relevant for FINANCIAL ANALYSIS,
such as Investor Relations, Financial Reports, Key Figures, Market Data, 
Annual Reports, Innovation pipeline, Strategic projects, and Partnerships.
Respond in JSON as in this example:
{
    "links": [
        {"type": "investor relations", "url": "https://full.url/investors"},
        {"type": "financial reports", "url": "https://full.url/annual-report"},
        {"type": "innovation projects", "url": "https://full.url/innovation"}
    ]
}
"""


def get_links_user_prompt(website):
    user_prompt = f"Here is the list of links on the website of {website.url} - "
    user_prompt += "please decide which of these are relevant web links for a brochure about the company, respond with the full https URL in JSON format. \
Do not include Terms of Service, Privacy, email links.\n"
    user_prompt += "Links (some might be relative links):\n"
    user_prompt += "\n".join(website.links)
    return user_prompt
# print(get_links_user_prompt(oct))


def get_links(url):
    website = Website(url)
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": link_system_prompt},
            {"role": "user", "content": get_links_user_prompt(website)}
      ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    return json.loads(result)
# Anthropic has made their site harder to scrape, so I'm using HuggingFace..


huggingface = Website("https://huggingface.co")
# print(huggingface.links)
# print(get_links("https://huggingface.co"))


# ############################################################################
# Second step: make the brochure!
# ############################################################################


def get_all_details(url):
    # Assemble all the details into another prompt to GPT4-o
    result = "Landing page:\n"
    result += Website(url).get_contents()
    links = get_links(url)
    # print("Found links:", links)
    for link in links["links"]:
        result += f"\n\n{link['type']}\n"
        result += Website(link["url"]).get_contents()
    return result

# print(get_all_details("https://huggingface.co"))


# create a system prompt with the context of all the details

################################ ORIENTE BROCHURE MARKETING
# system_prompt = "You are an assistant that analyzes the contents of several relevant pages from a company website \
# and creates a short brochure about the company for prospective customers, investors and recruits. Respond in markdown.\
# Include details of company culture, customers and careers/jobs if you have the information."

################################ ORIENTE PLUS HUMOURISTIQUE
# system_prompt = "You are an assistant that analyzes the contents of several relevant pages from a company website \
# and creates a short humorous, entertaining, jokey brochure about the company for prospective customers, investors and recruits. Respond in markdown.\
# Include details of company culture, customers and careers/jobs if you have the information."

############################## ORIENTE BROCHURE FINANCIERE
system_prompt = """
You are an assistant specialized in analyzing company information 
for FINANCIAL DECISION MAKERS.  
Given the content of relevant pages, produce a **concise investment briefing** in markdown format.

Focus on:
- Key financial metrics (revenue, EBITDA, margins, growth rates)
- Major innovations or new products
- Competitive positioning
- Strategic partnerships
- Market opportunities and risks

The output must include:
1. Executive Summary
2. Key Figures Table
3. Recent Innovations / Projects
4. Opportunities & Risks (bulleted)
5. Conclusion for investors

The output must be written in French
"""


def get_brochure_user_prompt(company_name, url):
    user_prompt = f"You are looking at a company called: {company_name}\n"
    user_prompt += f"Here are the contents of its landing page and other relevant pages; use this information to build a short brochure of the company in markdown.\n"
    user_prompt += get_all_details(url)
    # user_prompt = user_prompt[:5_000] # Truncate if more than 5,000 characters
    return user_prompt

# print(get_brochure_user_prompt("HuggingFace", "https://huggingface.co"))

# ############################################################################ RESPONSE WITHOUT STREAMING

def create_brochure(company_name, url):
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_brochure_user_prompt(company_name, url)}
          ],
    )
    result = response.choices[0].message.content
    return result
    # print(result)

# print(create_brochure("HuggingFace", "https://huggingface.co"))

# ############################################################################ STREAMING

# def stream_brochure(company_name, url):
#     stream = openai.chat.completions.create(
#         model=MODEL,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": get_brochure_user_prompt(company_name, url)}
#           ],
#         stream=True
#     )
    
#     response = ""
#     for chunk in stream:
#         response += chunk.choices[0].delta.content or ''
#         response = response.replace("```","").replace("markdown", "")

        
# # stream_brochure("HuggingFace", "https://huggingface.co")
# stream_brochure("Octime", "https://octime.com")


import asyncio
from openai import AsyncOpenAI

aiclient = AsyncOpenAI()

async def abrochure_chunks(company_name: str, url: str):
    stream = await aiclient.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_brochure_user_prompt(company_name, url)},
        ],
        stream=True,
    )
    async for chunk in stream:
        delta = getattr(chunk.choices[0], "delta", None)
        piece = getattr(delta, "content", "") if delta else ""
        if piece:
            yield piece.replace("```", "").replace("markdown", "")

# exemple d’usage (console)
async def arender_console(company_name: str, url: str):
    async for piece in abrochure_chunks(company_name, url):
        print(piece, end="", flush=True)
    print()

# asyncio.run(arender_console("HuggingFace", "https://huggingface.co"))
asyncio.run(arender_console("Octime", "https://octime.com"))


# ############################################################################
# Business applications
# In this exercise we extended the Day 1 code to make multiple LLM calls, and generate a document.
# This is perhaps the first example of Agentic AI design patterns, as we combined multiple calls to LLMs. This will feature more in Week 2, and then we will return to Agentic AI in a big way in Week 8 when we build a fully autonomous Agent solution.

# Generating content in this way is one of the very most common Use Cases. As with summarization, this can be applied to any business vertical. Write marketing content, generate a product tutorial from a spec, create personalized email content, and so much more. Explore how you can apply content generation to your business, and try making yourself a proof-of-concept prototype. See what other students have done in the community-contributions folder -- so many valuable projects -- it's wild!

	
# Before you move to Week 2 (which is tons of fun)
# Please see the week1 EXERCISE notebook for your challenge for the end of week 1. This will give you some essential practice working with Frontier APIs, and prepare you well for Week 2.
	
# A reminder on 3 useful resources
# 1. The resources for the course are available here.
# 2. I'm on LinkedIn here and I love connecting with people taking the course!
# 3. I'm trying out X/Twitter and I'm at @edwarddonner and hoping people will teach me how it's done..
	
# Finally! I have a special request for you
# My editor tells me that it makes a MASSIVE difference when students rate this course on Udemy - it's one of the main ways that Udemy decides whether to show it to others. If you're able to take a minute to rate this, I'd be so very grateful! And regardless - always please reach out to me at ed@edwarddonner.com if I can help at any point.
 