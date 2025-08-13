#!/usr/bin/env python3
"""
NeuralSync AI Communication Bus
==============================

Real-time WebSocket-based communication system for AI agents.
Enables seamless message passing, broadcasting, and coordination
between multiple AI agents with features like:

- Agent registration and discovery
- Direct agent-to-agent messaging  
- Broadcast messaging
- Message routing and delivery confirmation
- Connection management and health monitoring
- Rate limiting and security
- Metrics and monitoring integration
"""

import asyncio
import json
import logging
import os
import ssl
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import websockets
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configure logging
logging.basicConfig(
    level=os.getenv("NEURALSYNC_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
BUS_HOST = os.getenv("NEURALSYNC_BUS_HOST", "0.0.0.0")
BUS_PORT = int(os.getenv("NEURALSYNC_BUS_PORT", "8765"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Security configuration
ENABLE_TLS = os.getenv("NEURALSYNC_ENABLE_TLS", "false").lower() == "true"
TLS_CERT_PATH = os.getenv("NEURALSYNC_TLS_CERT", "/etc/neuralsync/tls/cert.pem")
TLS_KEY_PATH = os.getenv("NEURALSYNC_TLS_KEY", "/etc/neuralsync/tls/key.pem")
API_TOKEN = os.getenv("NEURALSYNC_API_TOKEN", "")

# Feature flags
ENABLE_METRICS = os.getenv("NEURALSYNC_ENABLE_METRICS", "true").lower() == "true"
ENABLE_PERSISTENCE = os.getenv("NEURALSYNC_ENABLE_PERSISTENCE", "true").lower() == "true"
ENABLE_RATE_LIMITING = os.getenv("NEURALSYNC_ENABLE_RATE_LIMITING", "true").lower() == "true"
DEBUG = os.getenv("NEURALSYNC_DEBUG", "false").lower() == "true"

# Rate limiting configuration
MAX_MESSAGES_PER_MINUTE = int(os.getenv("NEURALSYNC_RATE_LIMIT", "60"))
MAX_CONNECTIONS_PER_IP = int(os.getenv("NEURALSYNC_MAX_CONNECTIONS", "10"))

# Metrics
if ENABLE_METRICS:
    connected_agents = Gauge('neuralsync_bus_connected_agents', 'Number of connected agents')
    total_connections = Gauge('neuralsync_bus_total_connections', 'Total active connections')
    messages_sent = Counter('neuralsync_bus_messages_total', 'Messages sent', ['message_type', 'status'])
    message_delivery_time = Histogram('neuralsync_bus_delivery_duration_seconds', 'Message delivery time')
    connection_duration = Histogram('neuralsync_bus_connection_duration_seconds', 'Connection duration')

class MessageType(Enum):
    """Message types supported by the bus."""
    AGENT_REGISTER = "agent_register"
    AGENT_DEREGISTER = "agent_deregister"
    DIRECT_MESSAGE = "direct_message"
    BROADCAST = "broadcast"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    ACK = "ack"
    SYSTEM = "system"

@dataclass
class BusMessage:
    """Standard message format for the AI bus."""
    type: MessageType
    from_agent: str
    to_agent: Optional[str] = None
    content: Any = None
    timestamp: float = None
    message_id: str = None
    correlation_id: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AgentInfo:
    """Information about a connected agent."""
    name: str
    websocket: websockets.WebSocketServerProtocol
    connected_at: float
    last_ping: float
    capabilities: List[str] = None
    metadata: Dict[str, Any] = None
    message_count: int = 0
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}

class ConnectionManager:
    """Manages WebSocket connections and agent registration."""
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.agents: Dict[str, AgentInfo] = {}
        self.ip_connections: Dict[str, Set[str]] = {}
        self.message_rates: Dict[str, List[float]] = {}
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize the connection manager."""
        if ENABLE_PERSISTENCE:
            try:
                self.redis_client = redis.from_url(REDIS_URL)
                await self.redis_client.ping()
                logger.info("Redis connection established for persistence")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
    
    async def register_connection(self, websocket: websockets.WebSocketServerProtocol, 
                                connection_id: str) -> bool:
        """Register a new WebSocket connection."""
        client_ip = websocket.remote_address[0]
        
        # Check IP-based connection limits
        if client_ip not in self.ip_connections:
            self.ip_connections[client_ip] = set()
        
        if len(self.ip_connections[client_ip]) >= MAX_CONNECTIONS_PER_IP:
            logger.warning(f"Connection limit exceeded for IP {client_ip}")
            return False
        
        self.connections[connection_id] = websocket
        self.ip_connections[client_ip].add(connection_id)
        
        if ENABLE_METRICS:
            total_connections.set(len(self.connections))
        
        logger.info(f"Connection registered: {connection_id} from {client_ip}")
        return True
    
    async def register_agent(self, connection_id: str, agent_name: str, 
                           capabilities: List[str] = None, 
                           metadata: Dict[str, Any] = None) -> bool:
        """Register an agent with the bus."""
        if connection_id not in self.connections:
            logger.error(f"Attempt to register agent {agent_name} with unknown connection {connection_id}")
            return False
        
        if agent_name in self.agents:
            logger.warning(f"Agent {agent_name} already registered, updating connection")
            await self.deregister_agent(agent_name)
        
        websocket = self.connections[connection_id]
        agent_info = AgentInfo(
            name=agent_name,
            websocket=websocket,
            connected_at=time.time(),
            last_ping=time.time(),
            capabilities=capabilities or [],
            metadata=metadata or {}
        )
        
        self.agents[agent_name] = agent_info
        
        # Persist agent registration
        if self.redis_client:
            await self.redis_client.hset(
                "neuralsync:agents",
                agent_name,
                json.dumps({
                    "connected_at": agent_info.connected_at,
                    "capabilities": agent_info.capabilities,
                    "metadata": agent_info.metadata
                })
            )
        
        if ENABLE_METRICS:
            connected_agents.set(len(self.agents))
        
        logger.info(f"Agent registered: {agent_name} with capabilities {capabilities}")
        return True
    
    async def deregister_agent(self, agent_name: str) -> bool:
        """Deregister an agent from the bus."""
        if agent_name not in self.agents:
            return False
        
        agent_info = self.agents.pop(agent_name)
        
        # Update connection duration metric
        if ENABLE_METRICS:
            duration = time.time() - agent_info.connected_at
            connection_duration.observe(duration)
            connected_agents.set(len(self.agents))
        
        # Remove from persistence
        if self.redis_client:
            await self.redis_client.hdel("neuralsync:agents", agent_name)
        
        logger.info(f"Agent deregistered: {agent_name}")
        return True
    
    async def deregister_connection(self, connection_id: str, websocket: websockets.WebSocketServerProtocol):
        """Deregister a WebSocket connection and any associated agents."""
        # Find and deregister agents using this connection
        agents_to_remove = []
        for agent_name, agent_info in self.agents.items():
            if agent_info.websocket == websocket:
                agents_to_remove.append(agent_name)
        
        for agent_name in agents_to_remove:
            await self.deregister_agent(agent_name)
        
        # Remove connection
        self.connections.pop(connection_id, None)
        
        # Update IP connection tracking
        client_ip = websocket.remote_address[0]
        if client_ip in self.ip_connections:
            self.ip_connections[client_ip].discard(connection_id)
            if not self.ip_connections[client_ip]:
                del self.ip_connections[client_ip]
        
        if ENABLE_METRICS:
            total_connections.set(len(self.connections))
        
        logger.info(f"Connection deregistered: {connection_id}")
    
    def get_agent_websocket(self, agent_name: str) -> Optional[websockets.WebSocketServerProtocol]:
        """Get WebSocket for a specific agent."""
        agent_info = self.agents.get(agent_name)
        return agent_info.websocket if agent_info else None
    
    def get_all_agent_names(self) -> List[str]:
        """Get list of all registered agent names."""
        return list(self.agents.keys())
    
    def is_rate_limited(self, agent_name: str) -> bool:
        """Check if agent is rate limited."""
        if not ENABLE_RATE_LIMITING:
            return False
        
        now = time.time()
        minute_ago = now - 60
        
        if agent_name not in self.message_rates:
            self.message_rates[agent_name] = []
        
        # Clean old messages
        self.message_rates[agent_name] = [
            msg_time for msg_time in self.message_rates[agent_name] 
            if msg_time > minute_ago
        ]
        
        # Check rate limit
        if len(self.message_rates[agent_name]) >= MAX_MESSAGES_PER_MINUTE:
            return True
        
        # Record this message
        self.message_rates[agent_name].append(now)
        return False
    
    async def update_agent_ping(self, agent_name: str):
        """Update last ping time for an agent."""
        if agent_name in self.agents:
            self.agents[agent_name].last_ping = time.time()

class AIBus:
    """Main AI communication bus service."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.running = False
        self.ssl_context = None
    
    async def initialize(self):
        """Initialize the AI bus."""
        logger.info("Initializing NeuralSync AI Bus")
        
        await self.connection_manager.initialize()
        
        # Set up TLS if enabled
        if ENABLE_TLS:
            if Path(TLS_CERT_PATH).exists() and Path(TLS_KEY_PATH).exists():
                self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                self.ssl_context.load_cert_chain(TLS_CERT_PATH, TLS_KEY_PATH)
                logger.info("TLS enabled")
            else:
                logger.warning("TLS requested but cert/key files not found, running without TLS")
        
        logger.info(f"AI Bus initialized on {BUS_HOST}:{BUS_PORT}")
    
    async def authenticate_connection(self, websocket: websockets.WebSocketServerProtocol) -> bool:
        """Authenticate a new connection (if authentication is enabled)."""
        if not API_TOKEN:
            return True  # No authentication required
        
        try:
            # Wait for authentication message
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            auth_data = json.loads(auth_message)
            
            if auth_data.get("type") == "auth" and auth_data.get("token") == API_TOKEN:
                await websocket.send(json.dumps({
                    "type": "auth_success",
                    "message": "Authentication successful"
                }))
                return True
            else:
                await websocket.send(json.dumps({
                    "type": "auth_error",
                    "message": "Authentication failed"
                }))
                return False
                
        except (asyncio.TimeoutError, json.JSONDecodeError, KeyError):
            await websocket.send(json.dumps({
                "type": "auth_error",
                "message": "Authentication timeout or invalid format"
            }))
            return False
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, 
                           raw_message: str, connection_id: str) -> bool:
        """Handle incoming message from a client."""
        try:
            message_data = json.loads(raw_message)
            message_type = MessageType(message_data.get("type", "unknown"))
            
            if message_type == MessageType.AGENT_REGISTER:
                return await self.handle_agent_register(websocket, message_data, connection_id)
            
            elif message_type == MessageType.AGENT_DEREGISTER:
                return await self.handle_agent_deregister(websocket, message_data)
            
            elif message_type == MessageType.DIRECT_MESSAGE:
                return await self.handle_direct_message(websocket, message_data)
            
            elif message_type == MessageType.BROADCAST:
                return await self.handle_broadcast(websocket, message_data)
            
            elif message_type == MessageType.PING:
                return await self.handle_ping(websocket, message_data)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error(websocket, f"Unknown message type: {message_type}")
                return False
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid message format: {e}")
            await self.send_error(websocket, "Invalid message format")
            return False
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(websocket, "Internal error processing message")
            return False
    
    async def handle_agent_register(self, websocket: websockets.WebSocketServerProtocol, 
                                  message_data: Dict[str, Any], connection_id: str) -> bool:
        """Handle agent registration."""
        agent_name = message_data.get("agent_name")
        capabilities = message_data.get("capabilities", [])
        metadata = message_data.get("metadata", {})
        
        if not agent_name:
            await self.send_error(websocket, "Agent name is required for registration")
            return False
        
        success = await self.connection_manager.register_agent(
            connection_id, agent_name, capabilities, metadata
        )
        
        if success:
            response = BusMessage(
                type=MessageType.ACK,
                from_agent="bus",
                to_agent=agent_name,
                content={
                    "message": f"Agent {agent_name} registered successfully",
                    "registered_agents": self.connection_manager.get_all_agent_names()
                }
            )
            await self.send_message(websocket, response)
            
            # Notify other agents of new registration
            await self.broadcast_system_message({
                "event": "agent_joined",
                "agent_name": agent_name,
                "capabilities": capabilities
            }, exclude_agent=agent_name)
            
            if ENABLE_METRICS:
                messages_sent.labels(message_type="register", status="success").inc()
            
            return True
        else:
            await self.send_error(websocket, "Failed to register agent")
            return False
    
    async def handle_agent_deregister(self, websocket: websockets.WebSocketServerProtocol, 
                                    message_data: Dict[str, Any]) -> bool:
        """Handle agent deregistration."""
        agent_name = message_data.get("agent_name")
        
        if not agent_name:
            await self.send_error(websocket, "Agent name is required for deregistration")
            return False
        
        success = await self.connection_manager.deregister_agent(agent_name)
        
        if success:
            # Notify other agents
            await self.broadcast_system_message({
                "event": "agent_left",
                "agent_name": agent_name
            }, exclude_agent=agent_name)
            
            if ENABLE_METRICS:
                messages_sent.labels(message_type="deregister", status="success").inc()
        
        return success
    
    async def handle_direct_message(self, websocket: websockets.WebSocketServerProtocol, 
                                  message_data: Dict[str, Any]) -> bool:
        """Handle direct message between agents."""
        from_agent = message_data.get("from_agent")
        to_agent = message_data.get("to_agent")
        content = message_data.get("content")
        
        if not all([from_agent, to_agent, content]):
            await self.send_error(websocket, "Direct message requires from_agent, to_agent, and content")
            return False
        
        # Check rate limiting
        if self.connection_manager.is_rate_limited(from_agent):
            await self.send_error(websocket, "Rate limit exceeded")
            if ENABLE_METRICS:
                messages_sent.labels(message_type="direct", status="rate_limited").inc()
            return False
        
        # Get target agent websocket
        target_websocket = self.connection_manager.get_agent_websocket(to_agent)
        if not target_websocket:
            await self.send_error(websocket, f"Agent {to_agent} not found")
            if ENABLE_METRICS:
                messages_sent.labels(message_type="direct", status="agent_not_found").inc()
            return False
        
        # Create and send message
        message = BusMessage(
            type=MessageType.DIRECT_MESSAGE,
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            correlation_id=message_data.get("correlation_id")
        )
        
        start_time = time.time()
        await self.send_message(target_websocket, message)
        
        # Send delivery confirmation
        confirmation = BusMessage(
            type=MessageType.ACK,
            from_agent="bus",
            to_agent=from_agent,
            content={"message": f"Message delivered to {to_agent}"},
            correlation_id=message_data.get("correlation_id")
        )
        await self.send_message(websocket, confirmation)
        
        if ENABLE_METRICS:
            delivery_time = time.time() - start_time
            message_delivery_time.observe(delivery_time)
            messages_sent.labels(message_type="direct", status="delivered").inc()
        
        return True
    
    async def handle_broadcast(self, websocket: websockets.WebSocketServerProtocol, 
                             message_data: Dict[str, Any]) -> bool:
        """Handle broadcast message to all agents."""
        from_agent = message_data.get("from_agent")
        content = message_data.get("content")
        
        if not all([from_agent, content]):
            await self.send_error(websocket, "Broadcast requires from_agent and content")
            return False
        
        # Check rate limiting
        if self.connection_manager.is_rate_limited(from_agent):
            await self.send_error(websocket, "Rate limit exceeded")
            if ENABLE_METRICS:
                messages_sent.labels(message_type="broadcast", status="rate_limited").inc()
            return False
        
        message = BusMessage(
            type=MessageType.BROADCAST,
            from_agent=from_agent,
            content=content
        )
        
        delivered_count = 0
        for agent_name, agent_info in self.connection_manager.agents.items():
            if agent_name != from_agent:  # Don't send to sender
                try:
                    await self.send_message(agent_info.websocket, message)
                    delivered_count += 1
                except Exception as e:
                    logger.warning(f"Failed to deliver broadcast to {agent_name}: {e}")
        
        # Send delivery confirmation
        confirmation = BusMessage(
            type=MessageType.ACK,
            from_agent="bus",
            to_agent=from_agent,
            content={"message": f"Broadcast delivered to {delivered_count} agents"}
        )
        await self.send_message(websocket, confirmation)
        
        if ENABLE_METRICS:
            messages_sent.labels(message_type="broadcast", status="delivered").inc()
        
        return True
    
    async def handle_ping(self, websocket: websockets.WebSocketServerProtocol, 
                         message_data: Dict[str, Any]) -> bool:
        """Handle ping message."""
        agent_name = message_data.get("from_agent")
        
        if agent_name:
            await self.connection_manager.update_agent_ping(agent_name)
        
        pong = BusMessage(
            type=MessageType.PONG,
            from_agent="bus",
            to_agent=agent_name,
            content={"timestamp": time.time()}
        )
        await self.send_message(websocket, pong)
        
        return True
    
    async def send_message(self, websocket: websockets.WebSocketServerProtocol, 
                         message: BusMessage):
        """Send a message to a WebSocket."""
        try:
            message_json = json.dumps(asdict(message))
            await websocket.send(message_json)
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Attempted to send to closed connection")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def send_error(self, websocket: websockets.WebSocketServerProtocol, error_message: str):
        """Send error message to client."""
        error = BusMessage(
            type=MessageType.ERROR,
            from_agent="bus",
            content={"error": error_message}
        )
        await self.send_message(websocket, error)
    
    async def broadcast_system_message(self, content: Dict[str, Any], exclude_agent: str = None):
        """Broadcast system message to all connected agents."""
        message = BusMessage(
            type=MessageType.SYSTEM,
            from_agent="bus",
            content=content
        )
        
        for agent_name, agent_info in self.connection_manager.agents.items():
            if agent_name != exclude_agent:
                await self.send_message(agent_info.websocket, message)
    
    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection."""
        connection_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}:{time.time()}"
        
        logger.info(f"New connection: {connection_id}")
        
        # Register connection
        if not await self.connection_manager.register_connection(websocket, connection_id):
            await websocket.close(code=1008, reason="Connection limit exceeded")
            return
        
        # Authenticate if required
        if API_TOKEN and not await self.authenticate_connection(websocket):
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        try:
            async for message in websocket:
                if not await self.handle_message(websocket, message, connection_id):
                    logger.warning(f"Message handling failed for connection {connection_id}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"Connection error for {connection_id}: {e}")
            traceback.print_exc()
        finally:
            await self.connection_manager.deregister_connection(connection_id, websocket)
    
    async def start_server(self):
        """Start the WebSocket server."""
        self.running = True
        
        logger.info(f"Starting AI Bus server on {BUS_HOST}:{BUS_PORT}")
        
        server = await websockets.serve(
            self.handle_connection,
            BUS_HOST,
            BUS_PORT,
            ssl=self.ssl_context,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        
        logger.info(f"AI Bus server started ({'with TLS' if self.ssl_context else 'without TLS'})")
        
        await server.wait_closed()
        logger.info("AI Bus server stopped")

async def main():
    """Main entry point."""
    # Start metrics server if enabled
    if ENABLE_METRICS:
        metrics_port = int(os.getenv("NEURALSYNC_METRICS_PORT", "8082"))
        start_http_server(metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")
    
    bus = AIBus()
    
    try:
        await bus.initialize()
        await bus.start_server()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"AI Bus failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())