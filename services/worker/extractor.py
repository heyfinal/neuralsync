import os, time, json
from pathlib import Path
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

EVENT_LOG = Path(os.getenv("NS_EVENT_LOG","/app/volume/events.jsonl"))
QDRANT_URL = os.getenv("NS_QDRANT_URL","http://localhost:6333")
COLL = "neuralsync_mem"
DIM = 1536
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
use_openai = bool(OPENAI_API_KEY)
if use_openai:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

def embed(texts: List[str]):
    if use_openai:
        res = client.embeddings.create(model="text-embedding-3-large", input=texts)
        return [d.embedding for d in res.data]
    return [[(hash(t) % 997)/997.0 for _ in range(DIM)] for t in texts]

q = QdrantClient(url=QDRANT_URL)

def tail_events():
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    EVENT_LOG.touch(exist_ok=True)
    pos = 0
    while True:
        try:
            with EVENT_LOG.open() as f:
                f.seek(pos)
                lines = f.readlines()
                pos = f.tell()
            if lines:
                batch = [json.loads(x) for x in lines]
                texts = [b["text"] for b in batch]
                vecs = embed(texts)
                points = []
                for i, b in enumerate(batch):
                    pid = f"{int(b['ts']*1000)}-{i}"
                    points.append(PointStruct(id=pid, vector=vecs[i], payload=b))
                q.upsert(collection_name=COLL, points=points)
        except Exception as e:
            print("[worker] error:", e)
        time.sleep(0.5)

if __name__ == "__main__":
    print("[worker] extractor started; tailing events…")
    tail_events()
