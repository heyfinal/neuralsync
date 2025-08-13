# NeuralSync MCP Integration

This directory contains the Model Context Protocol (MCP) integration for NeuralSync, enabling seamless connectivity with Claude, GPT-4, and other MCP-compatible AI systems.

## What is MCP?

The Model Context Protocol (MCP) is an open standard created by Anthropic for connecting AI assistants to data sources and tools. It enables:

- **Unified Integration**: Single protocol for multiple AI providers
- **Secure Access**: Controlled access to external systems
- **Real-time Communication**: Live data and tool integration
- **Extensible Architecture**: Custom tools and data sources

## NeuralSync MCP Server

The NeuralSync MCP server (`mcp_server.py`) provides:

### Resources
- **Memory Search**: Access to the NeuralSync semantic memory system
- **Agent List**: Currently active AI agents
- **System Health**: Real-time system status monitoring
- **Thread Memory**: Complete conversation histories

### Tools
- **search_memory**: Semantic search through stored conversations
- **store_memory**: Add new information to the memory system  
- **send_message**: Communicate with other AI agents
- **get_system_info**: Retrieve system statistics and health
- **register_agent**: Add new agents to the system

### Prompts
- **memory_search**: Template for memory search and analysis
- **agent_coordination**: Multi-agent task coordination
- **system_analysis**: System health and performance analysis

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the MCP Server

```bash
python mcp_server.py
```

### 3. Connect from Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "neuralsync": {
      "command": "python",
      "args": ["/path/to/neuralsync/mcp/mcp_server.py"],
      "env": {
        "POSTGRES_URL": "postgresql://neuralsync:neuralsync@localhost:5432/neuralsync",
        "QDRANT_URL": "http://localhost:6333",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

### 4. Use the Python Client

```python
from mcp_client import connect_neuralsync

async with connect_neuralsync() as client:
    # Search memory
    results = await client.search_memory("Python coding examples")
    
    # Send message to agent
    await client.send_message("CodeAgent", "Review this implementation")
    
    # Get system health
    health = await client.get_health_status()
```

## Configuration

The MCP server uses the same environment variables as the main NeuralSync system:

```bash
# Database connections
POSTGRES_URL=postgresql://neuralsync:neuralsync@localhost:5432/neuralsync
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379

# AI provider keys
OPENAI_API_KEY=your_openai_key

# Optional: API endpoint
NEURALSYNC_API_URL=http://localhost:8080
```

## Integration Examples

### Claude Desktop

Once configured, you can use NeuralSync directly in Claude conversations:

```
Can you search the NeuralSync memory for information about Python async patterns and summarize what you find?
```

### Custom Applications

```python
import asyncio
from mcp_client import NeuralSyncMCPClient

async def ai_assistant():
    async with NeuralSyncMCPClient() as client:
        # Store user question
        await client.store_memory(
            thread_id="user_123",
            agent_name="assistant",
            message_type="user",
            content="How do I optimize database queries?"
        )
        
        # Search for relevant context
        context = await client.search_memory(
            "database optimization query performance",
            limit=5
        )
        
        # Generate response using context
        # ... (your AI logic here)
        
        # Store response
        await client.store_memory(
            thread_id="user_123",
            agent_name="assistant", 
            message_type="assistant",
            content=response
        )

asyncio.run(ai_assistant())
```

### Agent Coordination

```python
async def coordinate_agents():
    async with NeuralSyncMCPClient() as client:
        # Get active agents
        agents = await client.list_agents()
        
        # Send coordination message
        for agent in agents:
            if agent['name'].startswith('Code'):
                await client.send_message(
                    agent['name'],
                    "Please review the latest commits and provide feedback"
                )
```

## Security Considerations

### Access Control
- The MCP server respects NeuralSync's authentication system
- Database access is controlled by connection credentials
- Tool execution is limited to safe operations

### Data Privacy
- Memory searches respect thread-level isolation
- No sensitive credentials are exposed through the protocol
- All communications are logged for audit purposes

### Network Security
- Server runs locally by default
- Remote access requires explicit configuration
- TLS encryption available for production deployments

## Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check database connections
python -c "import asyncpg; asyncpg.connect('postgresql://neuralsync:neuralsync@localhost:5432/neuralsync')"

# Verify dependencies
pip install -r requirements.txt
```

**Claude can't connect:**
```json
// Verify paths in Claude config
{
  "mcpServers": {
    "neuralsync": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
```

**Search returns no results:**
- Ensure Qdrant is running and populated
- Check OPENAI_API_KEY for embedding generation
- Verify similarity_threshold isn't too high

### Debugging

Enable debug logging:

```bash
export NEURALSYNC_LOG_LEVEL=DEBUG
python mcp_server.py
```

Test individual tools:

```python
async with connect_neuralsync() as client:
    # Test system info
    info = await client.get_system_info()
    print(f"System status: {info}")
    
    # Test memory search
    results = await client.search_memory("test query")
    print(f"Search results: {results['count']}")
```

## Advanced Usage

### Custom Tools

Extend the MCP server with custom tools:

```python
@mcp_server.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    if name == "custom_analysis":
        # Your custom logic here
        return [types.TextContent(
            type="text",
            text=json.dumps({"result": "custom analysis complete"})
        )]
```

### Batch Operations

Process multiple operations efficiently:

```python
async def batch_memory_store(client, messages):
    tasks = []
    for msg in messages:
        task = client.store_memory(
            thread_id=msg['thread_id'],
            agent_name=msg['agent'],
            message_type=msg['type'],
            content=msg['content']
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### System Monitoring

Monitor NeuralSync health through MCP:

```python
async def health_monitor():
    async with connect_neuralsync() as client:
        while True:
            health = await client.get_health_status()
            
            if health.get('status') != 'healthy':
                # Alert logic here
                print(f"System degraded: {health}")
            
            await asyncio.sleep(60)  # Check every minute
```

## Contributing

To contribute to the MCP integration:

1. Follow the official MCP specification
2. Add comprehensive error handling
3. Include usage examples in docstrings
4. Test with multiple AI providers
5. Update documentation for new features

For more information, see the main NeuralSync documentation.