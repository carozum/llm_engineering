import json, uuid, pathlib
DATA_DIR = pathlib.Path("data_uploads")
DATA_DIR.mkdir(exist_ok=True)
INDEX_PATH = DATA_DIR / "index.json"

def load_index():
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return []

def save_index(items):
    INDEX_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
