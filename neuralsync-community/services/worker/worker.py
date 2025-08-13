#!/usr/bin/env python3
"""
NeuralSync Memory Processing Worker
===================================

Background worker service that handles:
- Event processing and embedding generation
- Memory consolidation and cleanup
- Graph relationship updates
- Batch processing of memory operations
- Data synchronization between storage layers

This worker runs continuously, processing tasks from the Redis queue
and updating the memory stores (PostgreSQL, Qdrant, Neo4j).
"""

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from py2neo import Graph
import redis.asyncio as redis
from openai import AsyncOpenAI
import anthropic
import numpy as np
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configure logging
logging.basicConfig(
    level=os.getenv("NEURALSYNC_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
WORKER_ID = os.getenv("NEURALSYNC_WORKER_ID", f"worker-{os.getpid()}")
CONCURRENCY = int(os.getenv("NEURALSYNC_WORKER_CONCURRENCY", "4"))
BATCH_SIZE = int(os.getenv("NEURALSYNC_BATCH_SIZE", "10"))
QUEUE_NAME = os.getenv("NEURALSYNC_QUEUE_NAME", "neuralsync:tasks")
DEAD_LETTER_QUEUE = os.getenv("NEURALSYNC_DLQ", "neuralsync:failed")

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
EMBEDDING_MODEL = os.getenv("NEURALSYNC_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("NEURALSYNC_EMBEDDING_DIMENSIONS", "1536"))

# Feature flags
ENABLE_METRICS = os.getenv("NEURALSYNC_ENABLE_METRICS", "true").lower() == "true"
DEBUG = os.getenv("NEURALSYNC_DEBUG", "false").lower() == "true"

# Metrics
if ENABLE_METRICS:
    tasks_processed = Counter('neuralsync_worker_tasks_total', 'Tasks processed', ['task_type', 'status'])
    processing_duration = Histogram('neuralsync_worker_duration_seconds', 'Task processing duration', ['task_type'])
    queue_size = Gauge('neuralsync_worker_queue_size', 'Current queue size')
    active_workers = Gauge('neuralsync_worker_active', 'Active workers')
    embedding_operations = Counter('neuralsync_worker_embeddings_total', 'Embeddings generated', ['model'])
    memory_consolidations = Counter('neuralsync_worker_consolidations_total', 'Memory consolidations')

class MemoryWorker:
    """Main worker class for processing memory operations."""
    
    def __init__(self):
        self.worker_id = WORKER_ID
        self.running = False
        self.tasks_in_progress = 0
        
        # Database connections
        self.db_pool = None
        self.qdrant_client = None
        self.neo4j_graph = None
        self.redis_client = None
        
        # AI clients
        self.openai_client = None
        self.anthropic_client = None
        
    async def initialize(self):
        """Initialize all database connections and AI clients."""
        logger.info(f"Initializing worker {self.worker_id}")
        
        try:
            # PostgreSQL
            self.db_pool = await asyncpg.create_pool(POSTGRES_URL)
            logger.info("PostgreSQL connection established")
            
            # Qdrant
            self.qdrant_client = QdrantClient(url=QDRANT_URL)
            
            # Ensure collection exists
            try:
                self.qdrant_client.get_collection("neuralsync_memory")
            except:
                self.qdrant_client.recreate_collection(
                    collection_name="neuralsync_memory",
                    vectors_config=VectorParams(size=EMBEDDING_DIMENSIONS, distance=Distance.COSINE)
                )
            logger.info("Qdrant connection established")
            
            # Neo4j
            self.neo4j_graph = Graph(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Test connection
            self.neo4j_graph.run("RETURN 1")
            logger.info("Neo4j connection established")
            
            # Redis
            self.redis_client = redis.from_url(REDIS_URL)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # AI clients
            if OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            
            if ANTHROPIC_API_KEY:
                self.anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized")
            
            if ENABLE_METRICS:
                active_workers.set(1)
            
            logger.info(f"Worker {self.worker_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            raise
    
    async def shutdown(self):
        """Clean shutdown of all connections."""
        logger.info(f"Shutting down worker {self.worker_id}")
        
        self.running = False
        
        # Wait for active tasks to complete
        max_wait = 30  # seconds
        waited = 0
        while self.tasks_in_progress > 0 and waited < max_wait:
            logger.info(f"Waiting for {self.tasks_in_progress} tasks to complete...")
            await asyncio.sleep(1)
            waited += 1
        
        # Close connections
        if self.db_pool:
            await self.db_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if ENABLE_METRICS:
            active_workers.set(0)
        
        logger.info("Worker shutdown complete")
    
    async def generate_embedding(self, text: str, model: str = None) -> Optional[List[float]]:
        """Generate embedding for text using configured AI provider."""
        if not model:
            model = EMBEDDING_MODEL
        
        try:
            if self.openai_client and "openai" in model.lower():
                response = await self.openai_client.embeddings.create(
                    model=model,
                    input=text
                )
                embedding = response.data[0].embedding
                
                if ENABLE_METRICS:
                    embedding_operations.labels(model=model).inc()
                
                return embedding
            
            # Fallback to simple hash-based embedding for testing
            else:
                # Simple deterministic embedding for development/testing
                hash_val = hash(text)
                embedding = [
                    (hash_val % (i + 1000)) / 1000.0 
                    for i in range(EMBEDDING_DIMENSIONS)
                ]
                return embedding
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def process_embedding_task(self, task_data: Dict[str, Any]) -> bool:
        """Process embedding generation task."""
        try:
            event_id = task_data["event_id"]
            content = task_data["content"]
            thread_id = task_data["thread_id"]
            agent_name = task_data["agent_name"]
            message_type = task_data["message_type"]
            metadata = task_data.get("metadata", {})
            
            logger.debug(f"Processing embedding for event {event_id}")
            
            # Generate embedding
            embedding = await self.generate_embedding(content)
            if not embedding:
                logger.warning(f"Failed to generate embedding for event {event_id}")
                return False
            
            # Update PostgreSQL with embedding
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE events SET embedding = $1 WHERE id = $2
                """, embedding, event_id)
            
            # Store in Qdrant
            point = PointStruct(
                id=event_id,
                vector=embedding,
                payload={
                    "thread_id": thread_id,
                    "agent_name": agent_name,
                    "message_type": message_type,
                    "content": content,
                    "metadata": metadata,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            self.qdrant_client.upsert(
                collection_name="neuralsync_memory",
                points=[point]
            )
            
            logger.debug(f"Embedding processed for event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process embedding task: {e}")
            return False
    
    async def process_graph_update_task(self, task_data: Dict[str, Any]) -> bool:
        """Process graph relationship update task."""
        try:
            event_id = task_data["event_id"]
            thread_id = task_data["thread_id"]
            agent_name = task_data["agent_name"]
            message_type = task_data["message_type"]
            content = task_data["content"]
            timestamp = task_data.get("timestamp", datetime.utcnow().isoformat())
            
            logger.debug(f"Processing graph update for event {event_id}")
            
            # Create or update nodes and relationships
            self.neo4j_graph.run("""
                MERGE (t:Thread {id: $thread_id})
                MERGE (a:Agent {name: $agent_name})
                MERGE (m:Message {id: $event_id})
                SET m.type = $message_type, 
                    m.content = $content, 
                    m.timestamp = datetime($timestamp)
                MERGE (a)-[:SENT]->(m)
                MERGE (m)-[:IN_THREAD]->(t)
                
                // Create temporal relationships
                WITH m, t
                MATCH (prev:Message)-[:IN_THREAD]->(t)
                WHERE prev.timestamp < m.timestamp AND prev.id <> m.id
                WITH m, prev
                ORDER BY prev.timestamp DESC
                LIMIT 1
                MERGE (prev)-[:FOLLOWED_BY]->(m)
            """, 
                thread_id=thread_id,
                agent_name=agent_name,
                event_id=event_id,
                message_type=message_type,
                content=content[:1000],  # Limit content length in graph
                timestamp=timestamp
            )
            
            logger.debug(f"Graph updated for event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process graph update task: {e}")
            return False
    
    async def process_memory_consolidation_task(self, task_data: Dict[str, Any]) -> bool:
        """Process memory consolidation task (cleanup, optimization)."""
        try:
            thread_id = task_data.get("thread_id")
            max_age_days = task_data.get("max_age_days", 30)
            
            logger.info(f"Processing memory consolidation for thread {thread_id}")
            
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            # Archive old events
            async with self.db_pool.acquire() as conn:
                if thread_id:
                    archived_count = await conn.fetchval("""
                        UPDATE events 
                        SET metadata = metadata || '{"archived": true}'::jsonb
                        WHERE thread_id = $1 AND timestamp < $2 
                        AND NOT (metadata ? 'archived')
                        RETURNING COUNT(*)
                    """, thread_id, cutoff_date)
                else:
                    archived_count = await conn.fetchval("""
                        UPDATE events 
                        SET metadata = metadata || '{"archived": true}'::jsonb
                        WHERE timestamp < $1 
                        AND NOT (metadata ? 'archived')
                        RETURNING COUNT(*)
                    """, cutoff_date)
            
            if ENABLE_METRICS:
                memory_consolidations.inc()
            
            logger.info(f"Archived {archived_count} old events")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process memory consolidation task: {e}")
            return False
    
    async def process_batch_task(self, task_data: Dict[str, Any]) -> bool:
        """Process batch operations task."""
        try:
            batch_type = task_data["batch_type"]
            items = task_data["items"]
            
            logger.info(f"Processing batch task: {batch_type} with {len(items)} items")
            
            if batch_type == "batch_embeddings":
                # Process multiple embeddings in batch
                success_count = 0
                for item in items:
                    if await self.process_embedding_task(item):
                        success_count += 1
                
                logger.info(f"Batch embeddings: {success_count}/{len(items)} successful")
                return success_count == len(items)
            
            elif batch_type == "batch_graph_updates":
                # Process multiple graph updates
                success_count = 0
                for item in items:
                    if await self.process_graph_update_task(item):
                        success_count += 1
                
                logger.info(f"Batch graph updates: {success_count}/{len(items)} successful")
                return success_count == len(items)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process batch task: {e}")
            return False
    
    async def process_task(self, task_data: Dict[str, Any]) -> bool:
        """Process a single task based on its type."""
        task_type = task_data.get("task_type", "unknown")
        
        if ENABLE_METRICS:
            start_time = time.time()
        
        try:
            self.tasks_in_progress += 1
            
            success = False
            if task_type == "embedding":
                success = await self.process_embedding_task(task_data)
            elif task_type == "graph_update":
                success = await self.process_graph_update_task(task_data)
            elif task_type == "memory_consolidation":
                success = await self.process_memory_consolidation_task(task_data)
            elif task_type == "batch":
                success = await self.process_batch_task(task_data)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                success = False
            
            if ENABLE_METRICS:
                duration = time.time() - start_time
                processing_duration.labels(task_type=task_type).observe(duration)
                tasks_processed.labels(
                    task_type=task_type,
                    status="success" if success else "failed"
                ).inc()
            
            return success
            
        except Exception as e:
            if ENABLE_METRICS:
                tasks_processed.labels(task_type=task_type, status="error").inc()
            logger.error(f"Task processing error: {e}")
            traceback.print_exc()
            return False
        
        finally:
            self.tasks_in_progress -= 1
    
    async def run_worker(self):
        """Main worker loop."""
        logger.info(f"Starting worker {self.worker_id}")
        self.running = True
        
        while self.running:
            try:
                # Get task from Redis queue (blocking pop with timeout)
                task_data = await self.redis_client.blpop([QUEUE_NAME], timeout=5)
                
                if not task_data:
                    continue  # Timeout, check if still running
                
                queue_name, task_json = task_data
                
                try:
                    task = json.loads(task_json)
                    logger.debug(f"Processing task: {task.get('task_type', 'unknown')}")
                    
                    success = await self.process_task(task)
                    
                    if not success:
                        # Move failed task to dead letter queue
                        await self.redis_client.rpush(DEAD_LETTER_QUEUE, task_json)
                        logger.warning(f"Task moved to DLQ: {task.get('task_type', 'unknown')}")
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in task: {task_json}")
                except Exception as e:
                    logger.error(f"Task processing failed: {e}")
                    # Move to DLQ
                    await self.redis_client.rpush(DEAD_LETTER_QUEUE, task_json)
                
                # Update queue size metric
                if ENABLE_METRICS:
                    current_queue_size = await self.redis_client.llen(QUEUE_NAME)
                    queue_size.set(current_queue_size)
                
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connections."""
        health = {
            "worker_id": self.worker_id,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "tasks_in_progress": self.tasks_in_progress,
            "services": {}
        }
        
        try:
            # PostgreSQL
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health["services"]["postgresql"] = "healthy"
        except:
            health["services"]["postgresql"] = "unhealthy"
            health["status"] = "degraded"
        
        try:
            # Qdrant
            self.qdrant_client.get_collections()
            health["services"]["qdrant"] = "healthy"
        except:
            health["services"]["qdrant"] = "unhealthy"
            health["status"] = "degraded"
        
        try:
            # Neo4j
            self.neo4j_graph.run("RETURN 1")
            health["services"]["neo4j"] = "healthy"
        except:
            health["services"]["neo4j"] = "unhealthy"
            health["status"] = "degraded"
        
        try:
            # Redis
            await self.redis_client.ping()
            health["services"]["redis"] = "healthy"
        except:
            health["services"]["redis"] = "unhealthy"
            health["status"] = "degraded"
        
        return health

async def main():
    """Main entry point."""
    # Start metrics server if enabled
    if ENABLE_METRICS:
        start_http_server(int(os.getenv("NEURALSYNC_METRICS_PORT", "8081")))
        logger.info("Metrics server started on port 8081")
    
    worker = MemoryWorker()
    
    try:
        await worker.initialize()
        
        # Start worker tasks
        tasks = []
        for i in range(CONCURRENCY):
            task = asyncio.create_task(worker.run_worker())
            tasks.append(task)
        
        logger.info(f"Started {CONCURRENCY} worker tasks")
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        traceback.print_exc()
    finally:
        await worker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())