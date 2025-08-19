import os
import json, pathlib
DATA_DIR = pathlib.Path("data_uploads")
DATA_DIR.mkdir(exist_ok=True)
INDEX_PATH = DATA_DIR / "index.json"

from utils_rag import get_collection
    
def load_index():
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return []


def save_index(items):
    INDEX_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_document(doc_id: str):
    # 1) supprimer le fichier
    idx = load_index()
    item = next((it for it in idx if it["id"] == doc_id), None)
    if item:
        p = pathlib.Path(item["path"])
        if p.exists():
            try: p.unlink()
            except: pass
            
    # 2) retirer de l’index
    idx = [it for it in idx if it["id"] != doc_id]
    save_index(idx)
    
    # 3) supprimer les chunks vecteurs (ids préfixés par doc_id-…)
    col = get_collection()
    try:
        col.delete(where={"doc_id": doc_id})
    except Exception:
        # pour compat older Chroma : fallback sur prefix ids si besoin
        pass
