"""  
RAG minimal :

indexe les PDF uploadés (texte extrait) en chunks,

filtre par sujet/année (et “chapters” en best-effort),

injecte des citations en system prompt,

affiche les sources utilisées dans l’UI.
"""

import pathlib, json, uuid
from pypdf import PdfReader
import io, os, re

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# Persistance Chroma locale
CHROMA_DIR = "chroma_data"
chroma_client = chromadb.Client(Settings(is_persistent=True, persist_directory=CHROMA_DIR))

# Un seule index (ou collection dans Chromadb) global (plus simple)
def get_collection():
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small",
    )
    name = "index_global"
    try:
        return chroma_client.get_collection(name=name, embedding_function=ef)
    except:
        return chroma_client.create_collection(name=name, embedding_function=ef)
    

# def extract_pdf_text(pdf_bytes: bytes) -> str:
#     reader = PdfReader(io.BytesIO(pdf_bytes))
#     parts = []
#     for i, page in enumerate(reader.pages):
#         txt = page.extract_text() or ""
#         parts.append(f"[Page {i+1}]\n{txt}")
#     return "\n\n".join(parts)


# def extract_pdf_text(pdf_bytes: bytes) -> str:
#     import io
#     from pypdf import PdfReader

#     try:
#         reader = PdfReader(io.BytesIO(pdf_bytes))
#         parts = []
#         for i, page in enumerate(reader.pages):
#             txt = page.extract_text() or ""
#             parts.append(f"[Page {i+1}]\n{txt}")
#         text = "\n\n".join(parts).strip()
#         if text:
#             return text
#     except Exception:
#         pass

#     # Fallback facultatif (pip install pymupdf)
#     try:
#         import fitz  # PyMuPDF
#         doc = fitz.open(stream=pdf_bytes, filetype="pdf")
#         parts = []
#         for i, page in enumerate(doc):
#             txt = page.get_text("text") or ""
#             parts.append(f"[Page {i+1}]\n{txt}")
#         text = "\n\n".join(parts).strip()
#         if text:
#             return text
#     except Exception:
#         pass

#     # Si toujours vide : probablement un scan → il faudra OCR (plus tard)
#     return ""


# def chunk_text(text: str, max_tokens: int = 800, overlap: int = 120):
#     # approx 4 chars/token
#     max_chars = max_tokens * 4
#     step = max_chars - overlap * 4
#     out, i = [], 0
#     while i < len(text):
#         out.append(text[i:i+max_chars])
#         i += step
#     return out


# def index_file_to_chroma(file_item: dict):
#     """
#     file_item: entrée de l’index {id, name, path, subject, year, chapters, kind}
#     """
#     if file_item["kind"] != "pdf":
#         return  # on indexe uniquement le texte PDF pour ce MVP
#     p = pathlib.Path(file_item["path"])
#     if not p.exists():
#         return
#     text = extract_pdf_text(p.read_bytes())
#     chunks = chunk_text(text)
#     if not chunks:
#         return
#     col = get_collection()
#     # ids uniques par chunk
#     ids = [f"{file_item['id']}-{i}" for i in range(len(chunks))]
#     chapters_csv = ",".join(file_item["chapters"]) if file_item.get("chapters") else ""

#     metas = [{
#         "doc_id": file_item["id"],
#         "source": file_item["name"],
#         "subject": file_item["subject"],
#         "year": file_item["year"],
#         "chapters": chapters_csv,   
#         "chunk": i
#     } for i in range(len(chunks))]
#     col.add(documents=chunks, metadatas=metas, ids=ids)



def describe_image_with_llm(img_bytes: bytes):
    # très court : tu peux router vers Claude/GPT/Gemini
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    import base64
    b64 = base64.b64encode(img_bytes).decode()
    msgs = [{"role":"user","content":[
        {"type":"text","text":"Décris précisément ce sujet d'exercice. Extrais les équations en LaTeX."},
        {"type":"image_url","image_url":{"url": f"data:image/png;base64,{b64}"}}
    ]}]
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=msgs)
    return resp.choices[0].message.content  # texte à indexer



def extract_pages(pdf_bytes: bytes):
    r = PdfReader(io.BytesIO(pdf_bytes))
    return [ (i+1, (p.extract_text() or "")) for i,p in enumerate(r.pages) ]  # [(page_num, text)]



def chunk_pages(pages, max_chars=3200, overlap_chars=400):
    # assemble des blocs multi-pages, mais on garde le range de pages
    blocks, cur, start_page = [], "", None
    for pg, txt in pages:
        if start_page is None: start_page = pg
        # limite : si on dépasse, on flush
        if len(cur) + len(txt) > max_chars and cur:
            end_page = pg-1
            blocks.append((start_page, end_page, cur.strip()))
            # overlap simple
            cur = cur[-overlap_chars:] + "\n"
            start_page = pg
        cur += f"[Page {pg}]\n{txt}\n\n"
    if cur.strip():
        blocks.append((start_page, pg, cur.strip()))
    return blocks  # [(page_start, page_end, text)]



def index_file_to_chroma(file_item: dict):
    if file_item["kind"] != "pdf":
        return
    p = pathlib.Path(file_item["path"])
    if not p.exists(): return

    pages = extract_pages(p.read_bytes())
    blocks = chunk_pages(pages)  # garde pages
    if not blocks: return

    col = get_collection()
    chapters_csv = ",".join(file_item.get("chapters") or [])
    ids, docs, metas = [], [], []
    for i, (p_start, p_end, content) in enumerate(blocks):
        ids.append(f"{file_item['id']}-{i}")
        docs.append(content)
        metas.append({
            "doc_id": file_item["id"],
            "source": file_item["name"],
            "subject": file_item["subject"],
            "year": file_item["year"],
            "chapters": chapters_csv,         # string pour Chroma
            "chunk": i,
            "page_start": int(p_start),       # scalaires -> OK
            "page_end": int(p_end)
        })
    col.add(documents=docs, metadatas=metas, ids=ids)


def rag_query(query: str, k: int, subject: str|None, year: str|None, chapters: list[str]|None):
    col = get_collection()
    where = {}
    if subject: where["subject"] = subject
    if year: where["year"] = year

    res = col.query(query_texts=[query], n_results=k*3, where=where or None)

    hits = []
    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i]
        # sécuriser meta["chapters"] -> set
        chap_str = (meta.get("chapters") or "").strip()
        chap_set = set([c.strip() for c in chap_str.split(",") if c.strip()])
        meta["chapters"] = chap_str  # on laisse une string dans meta, conforme Chroma
        hits.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "meta": meta,
            "chap_set": chap_set,     # helper interne pour filtrage
        })

    # Filtre “chapters” si fourni
    if chapters:
        want = set([c.strip() for c in chapters if c.strip()])
        filt = [h for h in hits if h["chap_set"] & want]
        hits = filt or hits
    # print(hits[:k])
    return hits[:k]



def _collapse_ws(s: str) -> str:
    return " ".join((s or "").split())


def build_system_prompt(base_system: str, rag_snippets: list[dict],
                        max_chars_total: int = 1800, max_chars_per_snip: int = 400) -> str:
    if not rag_snippets:
        return base_system + "\n(Aucun contexte RAG.)"

    blocks= []
    # used = 0
    for i, h in enumerate(rag_snippets, 1):
        meta = h["meta"]
        src = meta.get("source", "doc")
        chunk = meta.get("chunk", 0)
        subj = meta.get("subject", "")
        yr = meta.get("year", "")
        chs = meta.get("chapters") or ""  # string CSV côté Chroma
        txt = _collapse_ws(h.get("text", "")).strip()

        # tronquer intelligemment
        # if len(txt) > max_chars_per_snip:
        #     txt = txt[:max_chars_per_snip].rsplit(" ", 1)[0] + "…"

        block = f"[{i}] {src} • {subj}/{yr} • ch:{chs} • chunk {chunk}\n\"\"\"\n{txt}\n\"\"\""
        # if used + len(block) > max_chars_total:
        #     break
        blocks.append(block)
        # used += len(block)

    header = (
        base_system +
        "\nTu disposes des extraits suivants issus des documents de l'élève. "
        "Appuie-toi dessus, cite-les (numéro [i]) et n'invente pas d’info hors de ces extraits.\n\n" +
        "\n\n".join(blocks) +
        "\n—\n"
    )
    # print(header)
    return header


