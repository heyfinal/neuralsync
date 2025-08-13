#!/usr/bin/env python3
"""
NeuralSync MCP Client
====================

Client library for connecting to the NeuralSync MCP server.
Provides easy-to-use interface for AI applications to interact
with the NeuralSync ecosystem.

Example usage:

    from mcp_client import NeuralSyncMCPClient
    
    async with NeuralSyncMCPClient() as client:
        # Search memory
        results = await client.search_memory("Python examples")
        
        # Send message to agent
        await client.send_message("CodeAgent", "Process this file")
        
        # Get system status
        status = await client.get_system_info()
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager

from mcp.client import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class NeuralSyncMCPClient:
    """High-level client for NeuralSync MCP server."""
    
    def __init__(self, server_path: str = "python", server_args: List[str] = None):
        """Initialize the MCP client.
        
        Args:
            server_path: Path to the MCP server executable
            server_args: Arguments to pass to the server
        """
        if server_args is None:
            server_args = ["mcp_server.py"]
            
        self.server_params = StdioServerParameters(
            command=server_path,
            args=server_args
        )
        self.client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = await stdio_client(self.server_params).__aenter__()
        await self.client.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def search_memory(self, 
                           query: str, 
                           thread_id: Optional[str] = None,
                           agent_name: Optional[str] = None,
                           limit: int = 10,
                           similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """Search NeuralSync memory system.
        
        Args:
            query: Search query text
            thread_id: Optional thread filter
            agent_name: Optional agent filter
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Dictionary containing search results
        """
        args = {
            "query": query,
            "limit": limit,
            "similarity_threshold": similarity_threshold
        }
        
        if thread_id:
            args["thread_id"] = thread_id
        if agent_name:
            args["agent_name"] = agent_name
            
        result = await self.client.call_tool("search_memory", args)
        
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {"results": [], "count": 0}
    
    async def store_memory(self,
                          thread_id: str,
                          agent_name: str, 
                          message_type: str,
                          content: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Store a message in NeuralSync memory.
        
        Args:
            thread_id: Thread identifier
            agent_name: Agent name
            message_type: Type of message
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Storage result information
        """
        args = {
            "thread_id": thread_id,
            "agent_name": agent_name,
            "message_type": message_type,
            "content": content
        }
        
        if metadata:
            args["metadata"] = metadata
            
        result = await self.client.call_tool("store_memory", args)
        
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {"status": "error", "message": "No response from server"}
    
    async def send_message(self,
                          to_agent: str,
                          message: str,
                          message_type: str = "direct_message") -> Dict[str, Any]:
        """Send a message to another agent.
        
        Args:
            to_agent: Target agent name
            message: Message content
            message_type: Type of message
            
        Returns:
            Message delivery result
        """
        args = {
            "to_agent": to_agent,
            "message": message,
            "message_type": message_type
        }
        
        result = await self.client.call_tool("send_message", args)
        
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {"status": "error", "message": "No response from server"}
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get NeuralSync system information and statistics.
        
        Returns:
            System information dictionary
        """
        result = await self.client.call_tool("get_system_info", {})
        
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {"error": "No system information available"}
    
    async def register_agent(self,
                            name: str,
                            provider: str,
                            model: str,
                            config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Register a new agent with NeuralSync.
        
        Args:
            name: Agent name
            provider: AI provider
            model: Model name
            config: Optional configuration
            
        Returns:
            Registration result
        """
        args = {
            "name": name,
            "provider": provider,
            "model": model
        }
        
        if config:
            args["config"] = config
            
        result = await self.client.call_tool("register_agent", args)
        
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {"status": "error", "message": "Registration failed"}
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource by URI.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        result = await self.client.read_resource(uri)
        
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {"error": f"Resource not found: {uri}"}
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """Get list of active agents.
        
        Returns:
            List of agent information
        """
        result = await self.get_resource("neuralsync://agents/list")
        if isinstance(result, list):
            return result
        return []
    
    async def get_thread_memory(self, thread_id: str) -> Dict[str, Any]:
        """Get complete memory for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Thread memory information
        """
        return await self.get_resource(f"neuralsync://threads/{thread_id}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status.
        
        Returns:
            Health status information
        """
        return await self.get_resource("neuralsync://system/health")

# Convenience functions for quick usage
@asynccontextmanager
async def connect_neuralsync(server_path: str = "python", 
                           server_args: List[str] = None) -> AsyncContextManager[NeuralSyncMCPClient]:
    """Context manager for connecting to NeuralSync MCP server.
    
    Example:
        async with connect_neuralsync() as client:
            results = await client.search_memory("Python examples")
    """
    client = NeuralSyncMCPClient(server_path, server_args)
    async with client as connected_client:
        yield connected_client

# Example usage
async def main():
    """Example usage of the NeuralSync MCP client."""
    try:
        async with connect_neuralsync() as client:
            # Test system health
            health = await client.get_health_status()
            print("System Health:", json.dumps(health, indent=2))
            
            # List active agents
            agents = await client.list_agents()
            print(f"\nActive Agents ({len(agents)}):")
            for agent in agents:
                print(f"  - {agent.get('name', 'Unknown')}: {agent.get('model', 'Unknown model')}")
            
            # Search memory
            search_results = await client.search_memory("AI agent coordination")
            print(f"\nMemory Search Results: {search_results['count']} found")
            
            # Get system information
            sys_info = await client.get_system_info()
            print(f"\nSystem Info:")
            print(f"  - Events in memory: {sys_info.get('database', {}).get('events', 'Unknown')}")
            print(f"  - Active agents: {sys_info.get('database', {}).get('agents', 'Unknown')}")
            print(f"  - Unique threads: {sys_info.get('database', {}).get('threads', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"Error connecting to NeuralSync MCP server: {e}")
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())