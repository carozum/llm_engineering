# pip install fastapi uvicorn langgraph
from fastapi import FastAPI
from pydantic import BaseModel
from graph import app as graph_app  # LangGraph compilé

class ChatIn(BaseModel):
    user_id: str
    messages: list  # [{role, content}]
    subject: str | None = None

app = FastAPI()

@app.post("/chat")
def chat(inp: ChatIn):
    state = {"query": inp.messages[-1]["content"], "subject": inp.subject or "maths", "context": [], "plan":"", "answer":""}
    out = graph_app.invoke(state)
    return {"answer": out["answer"]}
