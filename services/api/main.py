import os, json, time
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from py2neo import Graph as NeoGraph

EVENT_LOG = os.getenv("NS_EVENT_LOG","/app/volume/events.jsonl")
QDRANT_URL = os.getenv("NS_QDRANT_URL","http://localhost:6333")
NEO_URL = os.getenv("NS_NEO4J_URL","bolt://localhost:7687")
NEO_USER = os.getenv("NS_NEO4J_USER","neo4j")
NEO_PASS = os.getenv("NS_NEO4J_PASS","password")
COLL = "neuralsync_mem"
API_TOKEN = os.getenv("NEURALSYNC_API_TOKEN","")

app = FastAPI(title="NeuralSync API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def require_token(auth: str | None):
  if not API_TOKEN: return
  if not auth or not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="Unauthorized")
  token = auth.split(" ",1)[1]
  if token != API_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")

q = QdrantClient(url=QDRANT_URL)
try:
    q.get_collection(COLL)
except:
    q.recreate_collection(collection_name=COLL, vectors_config=VectorParams(size=1536, distance=Distance.COSINE))
graph = NeoGraph(NEO_URL, auth=(NEO_USER, NEO_PASS))

class Event(BaseModel):
    thread_uid: str
    role: str
    text: str
    ts: float = time.time()
    meta: Dict[str,Any] = {}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/events/ingest")
def ingest(ev: Event, authorization: str | None = Header(default=None)):
    require_token(authorization)
    os.makedirs(os.path.dirname(EVENT_LOG), exist_ok=True)
    with open(EVENT_LOG,"a") as f:
        f.write(json.dumps(ev.dict())+"\n")
    graph.run("MERGE (t:Thread {uid:$uid})", uid=ev.thread_uid)
    graph.run("MERGE (a:Agent {name:$name})", name=ev.role)
    graph.run("MATCH (t:Thread {uid:$uid}),(a:Agent {name:$name}) MERGE (a)-[:PART_OF]->(t)", uid=ev.thread_uid, name=ev.role)
    return {"status":"ok"}

class SearchReq(BaseModel):
    query: str
    k: int = 8

@app.post("/memory/search")
def memory_search(req: SearchReq, authorization: str | None = Header(default=None)):
    require_token(authorization)
    out=[]
    try:
        with open(EVENT_LOG) as f:
            for line in f:
                out.append(json.loads(line))
    except FileNotFoundError:
        pass
    return {"items": out[-req.k:]}
