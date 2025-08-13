#!/usr/bin/env python3
"""
NeuralSync Core API Service
============================

The main FastAPI application that provides the core NeuralSync API endpoints
for memory management, agent coordination, and system monitoring.

Features:
- RESTful API for memory operations
- WebSocket support for real-time communication
- Authentication and authorization
- Rate limiting and security
- Comprehensive monitoring and metrics
- Distributed tracing support
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import (
    Depends, 
    FastAPI, 
    HTTPException, 
    Header, 
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
    Request,
    status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, Field, validator
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from py2neo import Graph
import redis.asyncio as redis
import asyncpg
from openai import AsyncOpenAI
import anthropic

# Configure logging
logging.basicConfig(
    level=os.getenv("NEURALSYNC_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
API_HOST = os.getenv("NEURALSYNC_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("NEURALSYNC_API_PORT", "8080"))
API_TOKEN = os.getenv("NEURALSYNC_API_TOKEN", "")
JWT_SECRET = os.getenv("NEURALSYNC_JWT_SECRET", "neuralsync-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("NEURALSYNC_JWT_EXPIRATION_HOURS", "24"))

# Database connections
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://neuralsync:neuralsync@localhost:5432/neuralsync")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neuralsync")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# AI provider configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Feature flags
ENABLE_METRICS = os.getenv("NEURALSYNC_ENABLE_METRICS", "true").lower() == "true"
ENABLE_AUTH = os.getenv("NEURALSYNC_ENABLE_AUTH", "true").lower() == "true"
ENABLE_RATE_LIMITING = os.getenv("NEURALSYNC_ENABLE_RATE_LIMITING", "true").lower() == "true"
DEBUG = os.getenv("NEURALSYNC_DEBUG", "false").lower() == "true"

# Metrics
if ENABLE_METRICS:
    request_count = Counter('neuralsync_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
    request_duration = Histogram('neuralsync_request_duration_seconds', 'Request duration')
    active_connections = Gauge('neuralsync_active_connections', 'Active WebSocket connections')
    memory_operations = Counter('neuralsync_memory_operations_total', 'Memory operations', ['operation', 'status'])
    agent_messages = Counter('neuralsync_agent_messages_total', 'Agent messages', ['agent', 'message_type'])

# Global connections
db_pool = None
qdrant_client = None
neo4j_graph = None
redis_client = None
openai_client = None
anthropic_client = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str, agent_name: Optional[str] = None):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if agent_name:
            self.agent_connections[agent_name] = websocket
        if ENABLE_METRICS:
            active_connections.set(len(self.active_connections))
        logger.info(f"Client {client_id} connected{f' as agent {agent_name}' if agent_name else ''}")

    def disconnect(self, client_id: str, agent_name: Optional[str] = None):
        self.active_connections.pop(client_id, None)
        if agent_name:
            self.agent_connections.pop(agent_name, None)
        if ENABLE_METRICS:
            active_connections.set(len(self.active_connections))
        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_text(message)

    async def send_to_agent(self, message: dict, agent_name: str):
        websocket = self.agent_connections.get(agent_name)
        if websocket:
            await websocket.send_text(json.dumps(message))
            return True
        return False

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            try:
                await connection.send_text(message)
            except:
                pass  # Connection might be closed

manager = ConnectionManager()

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period

    async def dispatch(self, request: Request, call_next):
        if not ENABLE_RATE_LIMITING:
            return await call_next(request)
        
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        if redis_client:
            current = await redis_client.get(key)
            if current:
                if int(current) >= self.calls:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"}
                    )
                await redis_client.incr(key)
            else:
                await redis_client.setex(key, self.period, 1)
        
        return await call_next(request)

# Metrics middleware
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not ENABLE_METRICS:
            return await call_next(request)
            
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        request_duration.observe(duration)
        
        return response

# Authentication
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return user info."""
    if not ENABLE_AUTH:
        return {"sub": "anonymous", "scopes": ["read", "write"]}
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_api_token(authorization: str = Header(None)) -> bool:
    """Verify API token from header."""
    if not API_TOKEN:
        return True  # No token required if not set
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ", 1)[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")
    
    return True

# Database initialization
async def init_database():
    """Initialize database connections and create tables."""
    global db_pool, qdrant_client, neo4j_graph, redis_client, openai_client, anthropic_client
    
    try:
        # PostgreSQL
        db_pool = await asyncpg.create_pool(POSTGRES_URL)
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    thread_id VARCHAR(255) NOT NULL,
                    agent_name VARCHAR(255) NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    embedding vector(1536),
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    INDEX (thread_id, timestamp),
                    INDEX (agent_name, timestamp)
                );
                
                CREATE TABLE IF NOT EXISTS agents (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    provider VARCHAR(100) NOT NULL,
                    model VARCHAR(255) NOT NULL,
                    config JSONB DEFAULT '{}',
                    status VARCHAR(50) DEFAULT 'inactive',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS memory_bundles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    thread_id VARCHAR(255) NOT NULL,
                    bundle_data BYTEA NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
        
        # Qdrant
        qdrant_client = QdrantClient(url=QDRANT_URL)
        try:
            qdrant_client.get_collection("neuralsync_memory")
        except:
            qdrant_client.recreate_collection(
                collection_name="neuralsync_memory",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
        
        # Neo4j
        neo4j_graph = Graph(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))
        neo4j_graph.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE")
        neo4j_graph.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Thread) REQUIRE t.id IS UNIQUE")
        
        # Redis
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        
        # AI clients
        if OPENAI_API_KEY:
            openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        if ANTHROPIC_API_KEY:
            anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        
        logger.info("Database connections initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}")
        raise

async def close_database():
    """Close database connections."""
    global db_pool, redis_client
    
    if db_pool:
        await db_pool.close()
    
    if redis_client:
        await redis_client.close()
    
    logger.info("Database connections closed")

# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()

# FastAPI app
app = FastAPI(
    title="NeuralSync Core API",
    description="AI orchestration platform with persistent memory and cross-agent communication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=DEBUG
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else ["http://localhost:3000", "https://*.neuralsync.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"] if DEBUG else ["localhost", "*.neuralsync.com"])
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(MetricsMiddleware)

# Pydantic models
class AgentMessage(BaseModel):
    """Agent message model."""
    thread_id: str = Field(..., description="Thread identifier")
    agent_name: str = Field(..., description="Agent name")
    message_type: str = Field(..., description="Message type")
    content: str = Field(..., description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AgentRegistration(BaseModel):
    """Agent registration model."""
    name: str = Field(..., description="Unique agent name")
    provider: str = Field(..., description="AI provider (openai, anthropic, etc.)")
    model: str = Field(..., description="Model name")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")

class MemoryQuery(BaseModel):
    """Memory query model."""
    query: str = Field(..., description="Search query")
    thread_id: Optional[str] = Field(None, description="Filter by thread ID")
    agent_name: Optional[str] = Field(None, description="Filter by agent name")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")

class AuthToken(BaseModel):
    """Authentication token request."""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str
    expires_in: int

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database connections
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["services"]["postgresql"] = "healthy"
    except:
        health_status["services"]["postgresql"] = "unhealthy"
        health_status["status"] = "degraded"
    
    try:
        qdrant_client.get_collections()
        health_status["services"]["qdrant"] = "healthy"
    except:
        health_status["services"]["qdrant"] = "unhealthy"
        health_status["status"] = "degraded"
    
    try:
        neo4j_graph.run("RETURN 1")
        health_status["services"]["neo4j"] = "healthy"
    except:
        health_status["services"]["neo4j"] = "unhealthy"
        health_status["status"] = "degraded"
    
    try:
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except:
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    if not ENABLE_METRICS:
        return Response("Metrics disabled", media_type="text/plain")
    
    return Response(generate_latest(), media_type="text/plain")

# Authentication endpoint
@app.post("/auth/token", response_model=TokenResponse)
async def login(auth_data: AuthToken):
    """Generate authentication token."""
    # In production, validate against user database
    # For demo purposes, accept any username/password
    
    payload = {
        "sub": auth_data.username,
        "scopes": ["read", "write"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )

# Agent management endpoints
@app.post("/agents/register")
async def register_agent(
    agent: AgentRegistration,
    _: dict = Depends(verify_token),
    __: bool = Depends(verify_api_token)
):
    """Register a new agent."""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO agents (name, provider, model, config, status)
                VALUES ($1, $2, $3, $4, 'active')
                ON CONFLICT (name) 
                DO UPDATE SET provider = $2, model = $3, config = $4, 
                             status = 'active', updated_at = NOW()
            """, agent.name, agent.provider, agent.model, json.dumps(agent.config))
            
            # Create agent node in Neo4j
            neo4j_graph.run("""
                MERGE (a:Agent {name: $name})
                SET a.provider = $provider, a.model = $model, a.config = $config
            """, name=agent.name, provider=agent.provider, model=agent.model, 
                config=json.dumps(agent.config))
            
            logger.info(f"Agent {agent.name} registered successfully")
            return {"status": "success", "message": f"Agent {agent.name} registered"}
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent.name}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def list_agents(_: dict = Depends(verify_token)):
    """List all registered agents."""
    async with db_pool.acquire() as conn:
        agents = await conn.fetch("""
            SELECT name, provider, model, config, status, created_at, updated_at
            FROM agents
            ORDER BY name
        """)
        
        return [dict(agent) for agent in agents]

@app.delete("/agents/{agent_name}")
async def deregister_agent(
    agent_name: str,
    _: dict = Depends(verify_token),
    __: bool = Depends(verify_api_token)
):
    """Deregister an agent."""
    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE agents SET status = 'inactive', updated_at = NOW()
            WHERE name = $1
        """, agent_name)
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Agent not found")
        
        logger.info(f"Agent {agent_name} deregistered")
        return {"status": "success", "message": f"Agent {agent_name} deregistered"}

# Memory management endpoints
@app.post("/memory/store")
async def store_memory(
    message: AgentMessage,
    background_tasks: BackgroundTasks,
    _: dict = Depends(verify_token),
    __: bool = Depends(verify_api_token)
):
    """Store a message in memory."""
    try:
        # Store in PostgreSQL
        async with db_pool.acquire() as conn:
            event_id = await conn.fetchval("""
                INSERT INTO events (thread_id, agent_name, message_type, content, metadata)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, message.thread_id, message.agent_name, message.message_type, 
                message.content, json.dumps(message.metadata))
        
        # Background task for embedding and graph updates
        background_tasks.add_task(process_memory_async, event_id, message)
        
        if ENABLE_METRICS:
            memory_operations.labels(operation="store", status="success").inc()
            agent_messages.labels(agent=message.agent_name, message_type=message.message_type).inc()
        
        logger.info(f"Memory stored for thread {message.thread_id}")
        return {"status": "success", "event_id": event_id}
        
    except Exception as e:
        if ENABLE_METRICS:
            memory_operations.labels(operation="store", status="error").inc()
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_memory_async(event_id: int, message: AgentMessage):
    """Async processing of memory storage (embeddings, graph updates)."""
    try:
        # Generate embedding
        embedding = None
        if openai_client:
            response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=message.content
            )
            embedding = response.data[0].embedding
        
        # Update PostgreSQL with embedding
        if embedding:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE events SET embedding = $1 WHERE id = $2
                """, embedding, event_id)
            
            # Store in Qdrant
            qdrant_client.upsert(
                collection_name="neuralsync_memory",
                points=[
                    PointStruct(
                        id=event_id,
                        vector=embedding,
                        payload={
                            "thread_id": message.thread_id,
                            "agent_name": message.agent_name,
                            "message_type": message.message_type,
                            "content": message.content,
                            "metadata": message.metadata,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                ]
            )
        
        # Update Neo4j graph
        neo4j_graph.run("""
            MERGE (t:Thread {id: $thread_id})
            MERGE (a:Agent {name: $agent_name})
            MERGE (m:Message {id: $event_id})
            SET m.type = $message_type, m.content = $content, m.timestamp = datetime()
            MERGE (a)-[:SENT]->(m)
            MERGE (m)-[:IN_THREAD]->(t)
        """, thread_id=message.thread_id, agent_name=message.agent_name, 
            event_id=event_id, message_type=message.message_type, content=message.content)
        
        logger.debug(f"Async processing completed for event {event_id}")
        
    except Exception as e:
        logger.error(f"Async memory processing failed for event {event_id}: {e}")

@app.post("/memory/search")
async def search_memory(
    query: MemoryQuery,
    _: dict = Depends(verify_token),
    __: bool = Depends(verify_api_token)
):
    """Search memory using semantic similarity."""
    try:
        results = []
        
        if openai_client:
            # Generate query embedding
            response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query.query
            )
            query_embedding = response.data[0].embedding
            
            # Search in Qdrant
            search_result = qdrant_client.search(
                collection_name="neuralsync_memory",
                query_vector=query_embedding,
                limit=query.limit,
                score_threshold=query.similarity_threshold,
                query_filter={
                    "must": [
                        {"key": "thread_id", "match": {"value": query.thread_id}}
                        if query.thread_id else None,
                        {"key": "agent_name", "match": {"value": query.agent_name}}
                        if query.agent_name else None
                    ]
                } if query.thread_id or query.agent_name else None
            )
            
            results = [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                for point in search_result
            ]
        else:
            # Fallback to PostgreSQL text search
            async with db_pool.acquire() as conn:
                query_conditions = ["content ILIKE $1"]
                query_params = [f"%{query.query}%"]
                param_count = 1
                
                if query.thread_id:
                    param_count += 1
                    query_conditions.append(f"thread_id = ${param_count}")
                    query_params.append(query.thread_id)
                
                if query.agent_name:
                    param_count += 1
                    query_conditions.append(f"agent_name = ${param_count}")
                    query_params.append(query.agent_name)
                
                sql_query = f"""
                    SELECT id, thread_id, agent_name, message_type, content, metadata, timestamp
                    FROM events
                    WHERE {' AND '.join(query_conditions)}
                    ORDER BY timestamp DESC
                    LIMIT {query.limit}
                """
                
                rows = await conn.fetch(sql_query, *query_params)
                results = [dict(row) for row in rows]
        
        if ENABLE_METRICS:
            memory_operations.labels(operation="search", status="success").inc()
        
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        if ENABLE_METRICS:
            memory_operations.labels(operation="search", status="error").inc()
        logger.error(f"Memory search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/threads/{thread_id}")
async def get_thread_memory(
    thread_id: str,
    limit: int = 50,
    _: dict = Depends(verify_token)
):
    """Get all memory for a specific thread."""
    async with db_pool.acquire() as conn:
        events = await conn.fetch("""
            SELECT id, agent_name, message_type, content, metadata, timestamp
            FROM events
            WHERE thread_id = $1
            ORDER BY timestamp
            LIMIT $2
        """, thread_id, limit)
        
        return {
            "thread_id": thread_id,
            "events": [dict(event) for event in events],
            "count": len(events)
        }

# WebSocket endpoint for real-time communication
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time agent communication."""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "agent_register":
                    agent_name = message.get("agent_name")
                    if agent_name:
                        manager.agent_connections[agent_name] = websocket
                        await websocket.send_text(json.dumps({
                            "type": "registration_success",
                            "agent_name": agent_name
                        }))
                
                elif message.get("type") == "agent_message":
                    target_agent = message.get("target_agent")
                    if target_agent and await manager.send_to_agent(message, target_agent):
                        await websocket.send_text(json.dumps({
                            "type": "message_delivered",
                            "target_agent": target_agent
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "message_failed",
                            "target_agent": target_agent,
                            "error": "Agent not connected"
                        }))
                
                elif message.get("type") == "broadcast":
                    await manager.broadcast(json.dumps({
                        "type": "broadcast_message",
                        "from": client_id,
                        "content": message.get("content", "")
                    }))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON message"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)

# System information endpoint
@app.get("/system/info")
async def system_info(_: dict = Depends(verify_token)):
    """Get system information and statistics."""
    try:
        # Database statistics
        async with db_pool.acquire() as conn:
            event_count = await conn.fetchval("SELECT COUNT(*) FROM events")
            agent_count = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE status = 'active'")
            thread_count = await conn.fetchval("SELECT COUNT(DISTINCT thread_id) FROM events")
        
        # Qdrant statistics
        qdrant_info = qdrant_client.get_collection("neuralsync_memory")
        vector_count = qdrant_info.points_count
        
        # Neo4j statistics
        neo4j_stats = neo4j_graph.run("""
            MATCH (n) 
            RETURN labels(n)[0] as label, count(n) as count
        """).data()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "events": event_count,
                "agents": agent_count,
                "threads": thread_count,
                "vectors": vector_count
            },
            "graph": {stat["label"]: stat["count"] for stat in neo4j_stats},
            "connections": {
                "websocket": len(manager.active_connections),
                "agents": len(manager.agent_connections)
            },
            "features": {
                "metrics_enabled": ENABLE_METRICS,
                "auth_enabled": ENABLE_AUTH,
                "rate_limiting": ENABLE_RATE_LIMITING
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    )