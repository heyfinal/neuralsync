#!/usr/bin/env python3
"""
NeuralSync MCP (Model Context Protocol) Server
==============================================

Implements the Model Context Protocol for NeuralSync, enabling seamless
integration with Claude, GPT-4, and other MCP-compatible AI systems.

This server provides:
- Memory access and search capabilities
- Agent coordination and communication
- System monitoring and health checks
- Tool execution and workflow automation
- Integration with the NeuralSync ecosystem

Based on Anthropic's MCP specification v1.0
https://github.com/modelcontextprotocol/specification
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Union
from datetime import datetime
import traceback

# MCP Protocol implementation
from mcp import server, types
from mcp.server import Server
from mcp.server.stdio import stdio_server
import asyncpg
from qdrant_client import QdrantClient
import redis.asyncio as redis
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(
    level=os.getenv("NEURALSYNC_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://neuralsync:neuralsync@localhost:5432/neuralsync")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
NEURALSYNC_API_URL = os.getenv("NEURALSYNC_API_URL", "http://localhost:8080")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# MCP Server Information
MCP_SERVER_INFO = types.ServerInfo(
    name="neuralsync-mcp",
    version="1.0.0",
    capabilities=types.ServerCapabilities(
        resources=types.ResourcesCapability(),
        tools=types.ToolsCapability(),
        prompts=types.PromptsCapability(),
        logging=types.LoggingCapability()
    ),
    instructions="NeuralSync MCP Server provides access to AI orchestration capabilities including memory management, agent coordination, and system monitoring."
)

class NeuralSyncMCPServer:
    """Main MCP server class for NeuralSync integration."""
    
    def __init__(self):
        self.server = Server(MCP_SERVER_INFO.name)
        self.db_pool = None
        self.qdrant_client = None
        self.redis_client = None
        self.openai_client = None
        
    async def initialize(self):
        """Initialize database connections."""
        try:
            # PostgreSQL
            self.db_pool = await asyncpg.create_pool(POSTGRES_URL)
            logger.info("PostgreSQL connection established")
            
            # Qdrant
            self.qdrant_client = QdrantClient(url=QDRANT_URL)
            logger.info("Qdrant connection established")
            
            # Redis
            self.redis_client = redis.from_url(REDIS_URL)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # OpenAI
            if OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            
            logger.info("NeuralSync MCP Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise

# Create the server instance
mcp_server = NeuralSyncMCPServer()

# Resources - Data that the AI can access
@mcp_server.server.list_resources()
async def list_resources() -> List[types.Resource]:
    """List available resources."""
    return [
        types.Resource(
            uri="neuralsync://memory/search",
            name="Memory Search",
            mimeType="application/json",
            description="Search through NeuralSync memory system using semantic similarity"
        ),
        types.Resource(
            uri="neuralsync://agents/list",
            name="Active Agents",
            mimeType="application/json", 
            description="List of currently active AI agents in the system"
        ),
        types.Resource(
            uri="neuralsync://system/health",
            name="System Health",
            mimeType="application/json",
            description="Current health status of all NeuralSync components"
        ),
        types.Resource(
            uri="neuralsync://threads/{thread_id}",
            name="Thread Memory",
            mimeType="application/json",
            description="Complete conversation thread with all messages and context"
        )
    ]

@mcp_server.server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    try:
        if uri == "neuralsync://memory/search":
            # Return available search parameters
            return json.dumps({
                "description": "Memory search interface",
                "parameters": {
                    "query": "Search query text",
                    "thread_id": "Optional thread filter",
                    "agent_name": "Optional agent filter", 
                    "limit": "Maximum results (default: 10)",
                    "similarity_threshold": "Minimum similarity score (default: 0.7)"
                },
                "example": {
                    "query": "Python code examples",
                    "limit": 5,
                    "similarity_threshold": 0.8
                }
            })
            
        elif uri == "neuralsync://agents/list":
            # Get active agents from database
            if mcp_server.db_pool:
                async with mcp_server.db_pool.acquire() as conn:
                    agents = await conn.fetch("""
                        SELECT name, provider, model, status, created_at
                        FROM agents 
                        WHERE status = 'active'
                        ORDER BY name
                    """)
                    
                    return json.dumps([dict(agent) for agent in agents])
            
        elif uri == "neuralsync://system/health":
            # Get system health status
            health = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "healthy",
                "services": {}
            }
            
            # Check database connections
            try:
                async with mcp_server.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                health["services"]["postgresql"] = "healthy"
            except:
                health["services"]["postgresql"] = "unhealthy"
                health["status"] = "degraded"
            
            try:
                mcp_server.qdrant_client.get_collections()
                health["services"]["qdrant"] = "healthy"
            except:
                health["services"]["qdrant"] = "unhealthy"
                health["status"] = "degraded"
                
            try:
                await mcp_server.redis_client.ping()
                health["services"]["redis"] = "healthy"
            except:
                health["services"]["redis"] = "unhealthy"
                health["status"] = "degraded"
            
            return json.dumps(health)
            
        elif uri.startswith("neuralsync://threads/"):
            # Extract thread ID
            thread_id = uri.split("/")[-1]
            
            if mcp_server.db_pool:
                async with mcp_server.db_pool.acquire() as conn:
                    events = await conn.fetch("""
                        SELECT id, agent_name, message_type, content, metadata, timestamp
                        FROM events
                        WHERE thread_id = $1
                        ORDER BY timestamp
                    """, thread_id)
                    
                    return json.dumps({
                        "thread_id": thread_id,
                        "events": [dict(event) for event in events],
                        "count": len(events)
                    })
        
        return json.dumps({"error": "Resource not found"})
        
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        return json.dumps({"error": str(e)})

# Tools - Functions the AI can call
@mcp_server.server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="search_memory",
            description="Search NeuralSync memory using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "thread_id": {
                        "type": "string", 
                        "description": "Optional thread filter"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Optional agent filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 10
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "description": "Minimum similarity score",
                        "default": 0.7
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="store_memory",
            description="Store a new message in NeuralSync memory",
            inputSchema={
                "type": "object", 
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "Thread identifier"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Agent name"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Message type (user, assistant, system, etc.)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata",
                        "default": {}
                    }
                },
                "required": ["thread_id", "agent_name", "message_type", "content"]
            }
        ),
        types.Tool(
            name="send_message",
            description="Send a message to another agent via the AI bus",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_agent": {
                        "type": "string",
                        "description": "Target agent name"
                    },
                    "message": {
                        "type": "string", 
                        "description": "Message content"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Message type",
                        "default": "direct_message"
                    }
                },
                "required": ["to_agent", "message"]
            }
        ),
        types.Tool(
            name="get_system_info",
            description="Get NeuralSync system information and statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="register_agent",
            description="Register a new agent with the NeuralSync system",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Agent name"
                    },
                    "provider": {
                        "type": "string",
                        "description": "AI provider (openai, anthropic, etc.)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name"
                    },
                    "config": {
                        "type": "object",
                        "description": "Agent configuration",
                        "default": {}
                    }
                },
                "required": ["name", "provider", "model"]
            }
        )
    ]

@mcp_server.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[types.TextContent]:
    """Execute a tool call."""
    try:
        if name == "search_memory":
            query = arguments["query"]
            thread_id = arguments.get("thread_id")
            agent_name = arguments.get("agent_name")
            limit = arguments.get("limit", 10)
            similarity_threshold = arguments.get("similarity_threshold", 0.7)
            
            results = []
            
            if mcp_server.openai_client:
                # Generate query embedding
                response = await mcp_server.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query
                )
                query_embedding = response.data[0].embedding
                
                # Search in Qdrant
                search_result = mcp_server.qdrant_client.search(
                    collection_name="neuralsync_memory",
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=similarity_threshold,
                    query_filter={
                        "must": [
                            {"key": "thread_id", "match": {"value": thread_id}} if thread_id else None,
                            {"key": "agent_name", "match": {"value": agent_name}} if agent_name else None
                        ]
                    } if thread_id or agent_name else None
                )
                
                results = [
                    {
                        "id": point.id,
                        "score": point.score,
                        "content": point.payload.get("content", ""),
                        "thread_id": point.payload.get("thread_id", ""),
                        "agent_name": point.payload.get("agent_name", ""),
                        "timestamp": point.payload.get("timestamp", "")
                    }
                    for point in search_result
                ]
            
            else:
                # Fallback to PostgreSQL text search
                if mcp_server.db_pool:
                    async with mcp_server.db_pool.acquire() as conn:
                        query_conditions = ["content ILIKE $1"]
                        query_params = [f"%{query}%"]
                        param_count = 1
                        
                        if thread_id:
                            param_count += 1
                            query_conditions.append(f"thread_id = ${param_count}")
                            query_params.append(thread_id)
                        
                        if agent_name:
                            param_count += 1
                            query_conditions.append(f"agent_name = ${param_count}")
                            query_params.append(agent_name)
                        
                        sql_query = f"""
                            SELECT id, thread_id, agent_name, message_type, content, timestamp
                            FROM events
                            WHERE {' AND '.join(query_conditions)}
                            ORDER BY timestamp DESC
                            LIMIT {limit}
                        """
                        
                        rows = await conn.fetch(sql_query, *query_params)
                        results = [dict(row) for row in rows]
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "results": results,
                    "count": len(results),
                    "query": query
                }, indent=2)
            )]
            
        elif name == "store_memory":
            thread_id = arguments["thread_id"] 
            agent_name = arguments["agent_name"]
            message_type = arguments["message_type"]
            content = arguments["content"]
            metadata = arguments.get("metadata", {})
            
            if mcp_server.db_pool:
                async with mcp_server.db_pool.acquire() as conn:
                    event_id = await conn.fetchval("""
                        INSERT INTO events (thread_id, agent_name, message_type, content, metadata)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING id
                    """, thread_id, agent_name, message_type, content, json.dumps(metadata))
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "event_id": event_id,
                        "message": "Memory stored successfully"
                    })
                )]
            
        elif name == "send_message":
            to_agent = arguments["to_agent"]
            message = arguments["message"]
            message_type = arguments.get("message_type", "direct_message")
            
            # Send message via Redis to the AI bus
            if mcp_server.redis_client:
                message_data = {
                    "type": message_type,
                    "to_agent": to_agent,
                    "from_agent": "mcp_client",
                    "content": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await mcp_server.redis_client.rpush(
                    "neuralsync:messages",
                    json.dumps(message_data)
                )
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "message": f"Message sent to {to_agent}"
                    })
                )]
                
        elif name == "get_system_info":
            # Get comprehensive system information
            info = {
                "timestamp": datetime.utcnow().isoformat(),
                "database": {},
                "services": {},
                "agents": {}
            }
            
            if mcp_server.db_pool:
                async with mcp_server.db_pool.acquire() as conn:
                    info["database"]["events"] = await conn.fetchval("SELECT COUNT(*) FROM events")
                    info["database"]["agents"] = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE status = 'active'")
                    info["database"]["threads"] = await conn.fetchval("SELECT COUNT(DISTINCT thread_id) FROM events")
            
            if mcp_server.qdrant_client:
                try:
                    collection_info = mcp_server.qdrant_client.get_collection("neuralsync_memory")
                    info["services"]["qdrant"] = {
                        "status": "healthy",
                        "points_count": collection_info.points_count
                    }
                except:
                    info["services"]["qdrant"] = {"status": "unhealthy"}
            
            return [types.TextContent(
                type="text",
                text=json.dumps(info, indent=2)
            )]
            
        elif name == "register_agent":
            name = arguments["name"]
            provider = arguments["provider"]
            model = arguments["model"]
            config = arguments.get("config", {})
            
            if mcp_server.db_pool:
                async with mcp_server.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO agents (name, provider, model, config, status)
                        VALUES ($1, $2, $3, $4, 'active')
                        ON CONFLICT (name)
                        DO UPDATE SET provider = $2, model = $3, config = $4, 
                                     status = 'active', updated_at = NOW()
                    """, name, provider, model, json.dumps(config))
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "message": f"Agent {name} registered successfully"
                    })
                )]
        
        return [types.TextContent(
            type="text", 
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]
        
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        traceback.print_exc()
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]

# Prompts - Templates the AI can use
@mcp_server.server.list_prompts()
async def list_prompts() -> List[types.Prompt]:
    """List available prompts."""
    return [
        types.Prompt(
            name="memory_search",
            description="Search and analyze NeuralSync memory for relevant context",
            arguments=[
                types.PromptArgument(
                    name="query",
                    description="What to search for in memory",
                    required=True
                ),
                types.PromptArgument(
                    name="context",
                    description="Additional context for the search",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="agent_coordination",
            description="Coordinate with other agents in the NeuralSync system",
            arguments=[
                types.PromptArgument(
                    name="task",
                    description="Task that requires coordination",
                    required=True
                ),
                types.PromptArgument(
                    name="agents",
                    description="Comma-separated list of agents to coordinate with",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="system_analysis",
            description="Analyze NeuralSync system health and performance",
            arguments=[
                types.PromptArgument(
                    name="focus",
                    description="Specific area to analyze (memory, agents, performance)",
                    required=False
                )
            ]
        )
    ]

@mcp_server.server.get_prompt()
async def get_prompt(name: str, arguments: Dict[str, str]) -> types.GetPromptResult:
    """Get a specific prompt."""
    try:
        if name == "memory_search":
            query = arguments.get("query", "")
            context = arguments.get("context", "")
            
            prompt = f"""You are working with the NeuralSync AI orchestration system. Your task is to search through the system's memory for information related to: "{query}"

{'Additional context: ' + context if context else ''}

Use the search_memory tool to find relevant information. Analyze the results and provide a comprehensive summary of what you found, including:

1. Key findings and insights
2. Relevant patterns or trends
3. Connections between different pieces of information
4. Recommendations based on the retrieved information

Focus on providing actionable insights that can help with AI agent coordination and decision-making."""

            return types.GetPromptResult(
                description=f"Memory search for: {query}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=prompt)
                    )
                ]
            )
            
        elif name == "agent_coordination":
            task = arguments.get("task", "")
            agents = arguments.get("agents", "")
            
            prompt = f"""You are coordinating multiple AI agents in the NeuralSync system to accomplish the following task:

Task: {task}

{'Target agents: ' + agents if agents else 'Coordinate with all available agents as needed.'}

Your role is to:

1. Analyze the task requirements and break it down into subtasks
2. Identify which agents are best suited for each subtask
3. Send appropriate messages to coordinate the work
4. Monitor progress and ensure successful completion
5. Consolidate results and provide a comprehensive summary

Use the available tools to:
- Check system status and available agents
- Send coordination messages to other agents  
- Store important decisions and outcomes in memory
- Search memory for relevant context or similar past tasks

Provide clear, actionable coordination instructions and maintain transparency throughout the process."""

            return types.GetPromptResult(
                description=f"Agent coordination for: {task}",
                messages=[
                    types.PromptMessage(
                        role="user", 
                        content=types.TextContent(type="text", text=prompt)
                    )
                ]
            )
            
        elif name == "system_analysis":
            focus = arguments.get("focus", "general")
            
            prompt = f"""You are analyzing the NeuralSync AI orchestration system. Your focus area is: {focus}

Perform a comprehensive analysis including:

1. System Health Assessment
   - Check all service connections and status
   - Identify any performance issues or bottlenecks
   - Review error logs and unusual patterns

2. Agent Performance Analysis  
   - Evaluate active agents and their effectiveness
   - Identify coordination patterns and success rates
   - Recommend optimizations for agent workflows

3. Memory System Analysis
   - Assess memory storage utilization and growth trends
   - Evaluate search performance and relevance
   - Identify opportunities for memory optimization

4. Operational Recommendations
   - Suggest improvements for system efficiency
   - Identify potential issues before they become critical
   - Recommend scaling or configuration adjustments

Use all available tools to gather comprehensive data and provide actionable insights with specific recommendations."""

            return types.GetPromptResult(
                description=f"System analysis focused on: {focus}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=prompt)
                    )
                ]
            )
        
        raise ValueError(f"Unknown prompt: {name}")
        
    except Exception as e:
        logger.error(f"Error getting prompt {name}: {e}")
        raise

async def main():
    """Main entry point for the MCP server."""
    try:
        # Initialize the server
        await mcp_server.initialize()
        
        # Run the server
        async with stdio_server() as streams:
            await mcp_server.server.run(
                read_stream=streams[0],
                write_stream=streams[1],
                init_options={}
            )
            
    except Exception as e:
        logger.error(f"MCP server failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())