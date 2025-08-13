#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# =============================================================================
# NeuralSync Community Edition — AI Orchestration Platform
# =============================================================================
# PURPOSE
# - This is the community edition installer for NeuralSync.
# - It sets up a complete AI orchestration platform with memory persistence,
#   cross-AI communication, and distributed consensus mechanisms.
# - Designed for developers, researchers, and AI enthusiasts.
#
# WHAT IT DOES:
# - Installs dependencies and sets up the complete NeuralSync stack
# - Configures Docker containers for data persistence (PostgreSQL, Qdrant, Neo4j)
# - Sets up the AI communication bus for real-time agent coordination
# - Creates memory layers: event log + semantic vectors + temporal graph
# - Provides enterprise-grade monitoring and observability
# - Integrates with popular AI providers (OpenAI, Anthropic, etc.)
#
# USAGE:
#   ./neuralsync.sh install    # Install and configure NeuralSync
#   ./neuralsync.sh start      # Start all services
#   ./neuralsync.sh stop       # Stop all services
#   ./neuralsync.sh status     # Check system status
#   ./neuralsync.sh logs       # View system logs
#   ./neuralsync.sh upgrade    # Upgrade to latest version
# =============================================================================

# ---- Versioning & Configuration ---------------------------------------------
NEURALSYNC_VERSION="${NEURALSYNC_VERSION:-1.0.0-community}"
INSTALL_DIR="${NEURALSYNC_INSTALL_DIR:-${HOME}/neuralsync}"
CONFIG_DIR="${INSTALL_DIR}/config"
DATA_DIR="${INSTALL_DIR}/data"
LOGS_DIR="${INSTALL_DIR}/logs"
SCRIPTS_DIR="${INSTALL_DIR}/scripts"
BUS_DIR="${INSTALL_DIR}/bus"
AGENTS_DIR="${INSTALL_DIR}/agents"
DOCS_DIR="${INSTALL_DIR}/docs"
ENV_FILE="${INSTALL_DIR}/.env"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Logging functions
log_info() { printf "${CYAN}[INFO]${NC} %s\n" "$*"; }
log_success() { printf "${GREEN}[SUCCESS]${NC} %s\n" "$*"; }
log_warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
log_error() { printf "${RED}[ERROR]${NC} %s\n" "$*"; }
log_header() { printf "\n${BOLD}${BLUE}=== %s ===${NC}\n" "$*"; }

# System detection
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# ---- Banner ------------------------------------------------------------------
show_banner() {
cat <<'EOF'
                                                                                    
    ███╗   ██╗███████╗██╗   ██╗██████╗  █████╗ ██╗     ███████╗██╗   ██╗███╗   ██╗ ██████╗
    ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔══██╗██║     ██╔════╝╚██╗ ██╔╝████╗  ██║██╔════╝
    ██╔██╗ ██║█████╗  ██║   ██║██████╔╝███████║██║     ███████╗ ╚████╔╝ ██╔██╗ ██║██║     
    ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██╔══██║██║     ╚════██║  ╚██╔╝  ██║╚██╗██║██║     
    ██║ ╚████║███████╗╚██████╔╝██║  ██║██║  ██║███████╗███████║   ██║   ██║ ╚████║╚██████╗
    ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝
                                                                                          
                           🤖 AI Orchestration Platform 🤖
                              Community Edition v${NEURALSYNC_VERSION}

╭─────────────────────────────────────────────────────────────────────────────────────╮
│  NeuralSync enables seamless collaboration between AI agents with:                  │
│                                                                                     │
│  💾 Persistent Memory     - Event logs, semantic vectors, temporal graphs          │
│  🔄 Cross-AI Communication - Real-time agent coordination via WebSocket bus        │
│  🧠 Consensus Mechanisms  - Byzantine fault-tolerant decision making              │
│  📊 Rich Observability   - Metrics, tracing, and comprehensive monitoring         │
│  🔌 Extensible Architecture - Plugin system for custom agents and integrations    │
│                                                                                     │
│  Ready to revolutionize your AI development workflow!                              │
╰─────────────────────────────────────────────────────────────────────────────────────╯

EOF
}

# ---- Dependency Installation ------------------------------------------------
install_dependencies() {
    log_header "Installing System Dependencies"
    
    case "$OS" in
        darwin*)
            log_info "Detected macOS - installing dependencies via Homebrew"
            if ! command -v brew >/dev/null 2>&1; then
                log_warn "Homebrew not found. Please install Homebrew first:"
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                return 1
            fi
            
            brew update || true
            brew install --quiet \
                docker \
                docker-compose \
                jq \
                tmux \
                python3 \
                node \
                cmake \
                wget \
                curl \
                git \
                redis || log_warn "Some packages may already be installed"
            ;;
            
        linux*)
            log_info "Detected Linux - installing dependencies via package manager"
            if command -v apt-get >/dev/null 2>&1; then
                # Ubuntu/Debian
                sudo apt-get update -y
                sudo apt-get install -y \
                    docker.io \
                    docker-compose-plugin \
                    jq \
                    tmux \
                    python3 \
                    python3-pip \
                    nodejs \
                    npm \
                    cmake \
                    build-essential \
                    wget \
                    curl \
                    git \
                    redis-server
            elif command -v yum >/dev/null 2>&1; then
                # RHEL/CentOS/Fedora
                sudo yum install -y \
                    docker \
                    docker-compose \
                    jq \
                    tmux \
                    python3 \
                    python3-pip \
                    nodejs \
                    npm \
                    cmake \
                    gcc \
                    wget \
                    curl \
                    git \
                    redis
            else
                log_error "Unsupported Linux distribution. Please install dependencies manually."
                return 1
            fi
            
            # Start Docker service
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker "$USER"
            log_warn "Please log out and back in for Docker group changes to take effect"
            ;;
            
        *)
            log_error "Unsupported operating system: $OS"
            return 1
            ;;
    esac
    
    log_success "Dependencies installed successfully"
}

# ---- Environment Configuration ----------------------------------------------
configure_environment() {
    log_header "Configuring Environment"
    
    # Create directory structure
    log_info "Creating directory structure"
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOGS_DIR" "$SCRIPTS_DIR" \
             "$BUS_DIR" "$AGENTS_DIR" "$DOCS_DIR" \
             "$DATA_DIR/postgres" "$DATA_DIR/qdrant" "$DATA_DIR/neo4j" \
             "$DATA_DIR/minio" "$DATA_DIR/redis" "$DATA_DIR/prometheus" \
             "$DATA_DIR/grafana" "$CONFIG_DIR/ssl" "$CONFIG_DIR/nginx"
    
    # Create environment file if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "Creating environment configuration"
        cat > "$ENV_FILE" <<EOF
# NeuralSync Community Edition Configuration
# Generated on: $(date)

# System Configuration
NEURALSYNC_VERSION=$NEURALSYNC_VERSION
NEURALSYNC_MODE=community
NEURALSYNC_DEBUG=false
NEURALSYNC_LOG_LEVEL=INFO

# API Configuration
NEURALSYNC_API_HOST=0.0.0.0
NEURALSYNC_API_PORT=8080
NEURALSYNC_API_TOKEN=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
NEURALSYNC_JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

# AI Bus Configuration
NEURALSYNC_BUS_HOST=0.0.0.0
NEURALSYNC_BUS_PORT=8765
NEURALSYNC_BUS_ADDR=ws://127.0.0.1:8765

# AI Provider Configuration (Add your API keys here)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
COHERE_API_KEY=
GROQ_API_KEY=

# AI Model Configuration
NS_DEFAULT_MODEL=gpt-4o-mini
NS_EMBEDDING_MODEL=text-embedding-3-small
NS_LARGE_MODEL=gpt-4o
NS_CODE_MODEL=gpt-4o

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=neuralsync
POSTGRES_USER=neuralsync
POSTGRES_PASSWORD=neuralsync_$(openssl rand -hex 8 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(8))")

# Vector Database Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=

# Graph Database Configuration
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neuralsync_$(openssl rand -hex 8 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(8))")

# Object Storage Configuration
MINIO_HOST=localhost
MINIO_PORT=9000
MINIO_ACCESS_KEY=neuralsync
MINIO_SECRET_KEY=neuralsync_$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=neuralsync_$(openssl rand -hex 8 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(8))")
JAEGER_PORT=16686

# Security Configuration
NEURALSYNC_ENABLE_HTTPS=false
NEURALSYNC_SSL_CERT_PATH=$CONFIG_DIR/ssl/neuralsync.crt
NEURALSYNC_SSL_KEY_PATH=$CONFIG_DIR/ssl/neuralsync.key

# Feature Flags
NEURALSYNC_ENABLE_METRICS=true
NEURALSYNC_ENABLE_TRACING=true
NEURALSYNC_ENABLE_AUTHENTICATION=true
NEURALSYNC_ENABLE_RATE_LIMITING=true
NEURALSYNC_ENABLE_CACHING=true

# MCP (Model Context Protocol) Configuration
NEURALSYNC_ENABLE_MCP=true
MCP_SERVER_PORT=8766
EOF
    else
        log_info "Environment file already exists, skipping creation"
    fi
    
    log_success "Environment configured successfully"
}

# ---- Docker Compose Configuration -------------------------------------------
create_docker_compose() {
    log_header "Creating Docker Compose Configuration"
    
    cat > "$COMPOSE_FILE" <<'EOF'
version: '3.8'

name: neuralsync

services:
  # PostgreSQL with pgvector extension for event storage
  postgres:
    image: pgvector/pgvector:pg16
    container_name: neuralsync-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-neuralsync}
      POSTGRES_USER: ${POSTGRES_USER:-neuralsync}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-neuralsync}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./config/postgres-init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-neuralsync} -d ${POSTGRES_DB:-neuralsync}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant vector database for semantic memory
  qdrant:
    image: qdrant/qdrant:v1.9.2
    container_name: neuralsync-qdrant
    restart: unless-stopped
    ports:
      - "${QDRANT_PORT:-6333}:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
      QDRANT__SERVICE__GRPC_PORT: 6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Neo4j graph database for temporal relationships
  neo4j:
    image: neo4j:5.20-community
    container_name: neuralsync-neo4j
    restart: unless-stopped
    environment:
      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-neuralsync}
      NEO4J_server_memory_pagecache_size: 1G
      NEO4J_server_memory_heap_initial__size: 1G
      NEO4J_server_memory_heap_max__size: 2G
      NEO4J_dbms_security_procedures_unrestricted: "gds.*,apoc.*"
      NEO4J_dbms_security_procedures_allowlist: "gds.*,apoc.*"
    ports:
      - "${NEO4J_PORT:-7687}:7687"
      - "7474:7474"
    volumes:
      - ./data/neo4j:/data
      - ./data/neo4j/logs:/logs
      - ./data/neo4j/import:/var/lib/neo4j/import
      - ./data/neo4j/plugins:/plugins
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u ${NEO4J_USER:-neo4j} -p ${NEO4J_PASSWORD:-neuralsync} 'RETURN 1'"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Redis for caching and session storage
  redis:
    image: redis:7.2-alpine
    container_name: neuralsync-redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # MinIO for object storage
  minio:
    image: minio/minio:RELEASE.2024-06-13T22-53-53Z
    container_name: neuralsync-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-neuralsync}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-neuralsync123}
    ports:
      - "${MINIO_PORT:-9000}:9000"
      - "9001:9001"
    volumes:
      - ./data/minio:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus for metrics collection
  prometheus:
    image: prom/prometheus:v2.52.0
    container_name: neuralsync-prometheus
    restart: unless-stopped
    ports:
      - "${PROMETHEUS_PORT:-9090}:9090"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - ./data/prometheus:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  # Grafana for visualization
  grafana:
    image: grafana/grafana:11.0.0
    container_name: neuralsync-grafana
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-neuralsync}
      GF_INSTALL_PLUGINS: grafana-clock-panel,grafana-simple-json-datasource
    ports:
      - "${GRAFANA_PORT:-3000}:3000"
    volumes:
      - ./data/grafana:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning
      - ./config/grafana/dashboards:/var/lib/grafana/dashboards

  # Jaeger for distributed tracing
  jaeger:
    image: jaegertracing/all-in-one:1.57
    container_name: neuralsync-jaeger
    restart: unless-stopped
    ports:
      - "16686:16686"
      - "14268:14268"
      - "6831:6831/udp"
    environment:
      COLLECTOR_OTLP_ENABLED: true

  # NeuralSync Core API
  neuralsync-api:
    image: python:3.12-slim
    container_name: neuralsync-api
    restart: unless-stopped
    working_dir: /app
    environment:
      # Database connections
      POSTGRES_URL: postgresql://${POSTGRES_USER:-neuralsync}:${POSTGRES_PASSWORD:-neuralsync}@postgres:5432/${POSTGRES_DB:-neuralsync}
      QDRANT_URL: http://qdrant:6333
      NEO4J_URL: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USER:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-neuralsync}
      REDIS_URL: redis://redis:6379
      MINIO_URL: http://minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:-neuralsync}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:-neuralsync123}
      
      # API configuration
      NEURALSYNC_API_TOKEN: ${NEURALSYNC_API_TOKEN}
      NEURALSYNC_JWT_SECRET: ${NEURALSYNC_JWT_SECRET}
      
      # AI provider keys
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      COHERE_API_KEY: ${COHERE_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
      
      # Feature flags
      NEURALSYNC_ENABLE_METRICS: ${NEURALSYNC_ENABLE_METRICS:-true}
      NEURALSYNC_ENABLE_TRACING: ${NEURALSYNC_ENABLE_TRACING:-true}
      NEURALSYNC_DEBUG: ${NEURALSYNC_DEBUG:-false}
    ports:
      - "${NEURALSYNC_API_PORT:-8080}:8080"
    volumes:
      - ./services/api:/app
      - ./data/api:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - qdrant
      - neo4j
      - redis
      - minio
    command: >
      bash -c "
        pip install --no-cache-dir -r requirements.txt &&
        python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
      "

  # NeuralSync Memory Worker
  neuralsync-worker:
    image: python:3.12-slim
    container_name: neuralsync-worker
    restart: unless-stopped
    working_dir: /app
    environment:
      # Database connections
      POSTGRES_URL: postgresql://${POSTGRES_USER:-neuralsync}:${POSTGRES_PASSWORD:-neuralsync}@postgres:5432/${POSTGRES_DB:-neuralsync}
      QDRANT_URL: http://qdrant:6333
      NEO4J_URL: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USER:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-neuralsync}
      REDIS_URL: redis://redis:6379
      
      # AI provider keys
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      
      # Worker configuration
      NEURALSYNC_WORKER_CONCURRENCY: 4
      NEURALSYNC_DEBUG: ${NEURALSYNC_DEBUG:-false}
    volumes:
      - ./services/worker:/app
      - ./data/api:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - qdrant
      - neo4j
      - redis
      - neuralsync-api
    command: >
      bash -c "
        pip install --no-cache-dir -r requirements.txt &&
        python worker.py
      "

volumes:
  postgres_data:
  qdrant_data:
  neo4j_data:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: neuralsync-network
    driver: bridge
EOF

    log_success "Docker Compose configuration created"
}

# ---- Service Installation ---------------------------------------------------
install_services() {
    log_header "Installing NeuralSync Services"
    
    # Copy service files from the distribution
    log_info "Installing API service..."
    cp -r "$(dirname "$0")/services" "$INSTALL_DIR/"
    
    log_info "Installing AI bus..."
    cp -r "$(dirname "$0")/bus" "$INSTALL_DIR/"
    
    log_info "Installing agent templates..."
    cp -r "$(dirname "$0")/agents" "$INSTALL_DIR/"
    
    log_info "Installing MCP tools..."
    cp -r "$(dirname "$0")/mcp" "$INSTALL_DIR/"
    
    log_info "Installing configuration templates..."
    cp -r "$(dirname "$0")/config" "$INSTALL_DIR/"
    
    log_info "Installing documentation..."
    cp -r "$(dirname "$0")/docs" "$INSTALL_DIR/"
    
    log_success "Services installed successfully"
}

# ---- System Status Check ----------------------------------------------------
check_status() {
    log_header "NeuralSync System Status"
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "NeuralSync not installed. Run 'neuralsync.sh install' first."
        return 1
    fi
    
    cd "$INSTALL_DIR"
    
    # Check Docker containers
    log_info "Checking container status..."
    docker-compose ps
    
    # Check service health
    log_info "Checking service health..."
    
    # API health check
    if curl -s "http://localhost:${NEURALSYNC_API_PORT:-8080}/health" >/dev/null 2>&1; then
        log_success "API service is healthy"
    else
        log_error "API service is not responding"
    fi
    
    # Database health checks
    local postgres_port=${POSTGRES_PORT:-5432}
    if timeout 5 bash -c "</dev/tcp/localhost/$postgres_port" 2>/dev/null; then
        log_success "PostgreSQL is accessible"
    else
        log_error "PostgreSQL is not accessible"
    fi
    
    local qdrant_port=${QDRANT_PORT:-6333}
    if curl -s "http://localhost:$qdrant_port/healthz" >/dev/null 2>&1; then
        log_success "Qdrant is healthy"
    else
        log_error "Qdrant is not responding"
    fi
    
    local neo4j_port=7474
    if curl -s "http://localhost:$neo4j_port" >/dev/null 2>&1; then
        log_success "Neo4j is accessible"
    else
        log_error "Neo4j is not accessible"
    fi
}

# ---- Service Management -----------------------------------------------------
start_services() {
    log_header "Starting NeuralSync Services"
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "NeuralSync not installed. Run 'neuralsync.sh install' first."
        return 1
    fi
    
    cd "$INSTALL_DIR"
    
    # Load environment
    set -a
    source "$ENV_FILE"
    set +a
    
    log_info "Starting all services..."
    docker-compose up -d
    
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Display service URLs
    cat <<EOF

${GREEN}╭─────────────────────────────────────────────────────────────────────────────╮
│                          🎉 NeuralSync is running! 🎉                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 Management & Monitoring:                                               │
│  • API Documentation:    http://localhost:${NEURALSYNC_API_PORT:-8080}/docs                  │
│  • Grafana Dashboard:    http://localhost:${GRAFANA_PORT:-3000}                       │
│  • Prometheus Metrics:   http://localhost:${PROMETHEUS_PORT:-9090}                       │
│  • Jaeger Tracing:       http://localhost:${JAEGER_PORT:-16686}                      │
│                                                                             │
│  🗄️ Database Interfaces:                                                   │
│  • Neo4j Browser:        http://localhost:7474                             │
│  • MinIO Console:        http://localhost:9001                             │
│  • Qdrant Dashboard:     http://localhost:${QDRANT_PORT:-6333}/dashboard              │
│                                                                             │
│  🤖 AI Integration:                                                         │
│  • WebSocket Bus:        ws://localhost:${NEURALSYNC_BUS_PORT:-8765}                      │
│  • MCP Server:           http://localhost:${MCP_SERVER_PORT:-8766}                       │
│                                                                             │
│  📝 Logs & Status:                                                         │
│  • View logs:            ./neuralsync.sh logs                             │
│  • Check status:         ./neuralsync.sh status                           │
│  • Stop services:        ./neuralsync.sh stop                             │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯${NC}

EOF
    
    log_success "All services started successfully!"
    log_info "Run './neuralsync.sh status' to check system health"
}

stop_services() {
    log_header "Stopping NeuralSync Services"
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_warn "NeuralSync not found in current directory"
        return 1
    fi
    
    cd "$INSTALL_DIR"
    
    log_info "Stopping all services..."
    docker-compose down
    
    log_success "All services stopped successfully!"
}

# ---- Log Management ---------------------------------------------------------
show_logs() {
    log_header "NeuralSync Service Logs"
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "NeuralSync not installed"
        return 1
    fi
    
    cd "$INSTALL_DIR"
    
    if [[ -n "${1:-}" ]]; then
        log_info "Showing logs for service: $1"
        docker-compose logs -f --tail=100 "$1"
    else
        log_info "Showing logs for all services (press Ctrl+C to exit)"
        docker-compose logs -f --tail=50
    fi
}

# ---- Upgrade System ---------------------------------------------------------
upgrade_system() {
    log_header "Upgrading NeuralSync"
    
    log_info "Backing up current configuration..."
    backup_dir="${INSTALL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    cp -r "$INSTALL_DIR" "$backup_dir"
    log_success "Backup created at: $backup_dir"
    
    log_info "Downloading latest version..."
    # This would download the latest release in a real implementation
    log_warn "Upgrade functionality not yet implemented in community edition"
    log_info "Please download the latest release manually from GitHub"
    
    return 0
}

# ---- Setup API Keys ---------------------------------------------------------
setup_api_keys() {
    log_header "API Key Setup"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found. Run install first."
        return 1
    fi
    
    log_info "Setting up AI provider API keys..."
    
    echo "Enter your API keys (press Enter to skip):"
    
    read -r -p "OpenAI API Key: " openai_key
    if [[ -n "$openai_key" ]]; then
        sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" "$ENV_FILE"
        log_success "OpenAI API key configured"
    fi
    
    read -r -p "Anthropic API Key: " anthropic_key
    if [[ -n "$anthropic_key" ]]; then
        sed -i.bak "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$anthropic_key/" "$ENV_FILE"
        log_success "Anthropic API key configured"
    fi
    
    read -r -p "Cohere API Key: " cohere_key
    if [[ -n "$cohere_key" ]]; then
        sed -i.bak "s/COHERE_API_KEY=.*/COHERE_API_KEY=$cohere_key/" "$ENV_FILE"
        log_success "Cohere API key configured"
    fi
    
    read -r -p "Groq API Key: " groq_key
    if [[ -n "$groq_key" ]]; then
        sed -i.bak "s/GROQ_API_KEY=.*/GROQ_API_KEY=$groq_key/" "$ENV_FILE"
        log_success "Groq API key configured"
    fi
    
    log_info "API keys have been configured. Restart services to apply changes."
}

# ---- Main Installation Process ----------------------------------------------
install_neuralsync() {
    show_banner
    
    log_info "Starting NeuralSync Community Edition installation..."
    log_info "Installation directory: $INSTALL_DIR"
    
    # Check if already installed
    if [[ -f "$COMPOSE_FILE" ]]; then
        log_warn "NeuralSync appears to already be installed"
        read -r -p "Continue with reinstallation? [y/N] " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled"
            return 0
        fi
    fi
    
    # Run installation steps
    install_dependencies
    configure_environment
    create_docker_compose
    install_services
    
    log_success "Installation completed successfully!"
    
    echo
    log_info "Next steps:"
    echo "  1. Configure API keys: ./neuralsync.sh setup-keys"
    echo "  2. Start services: ./neuralsync.sh start"
    echo "  3. Check status: ./neuralsync.sh status"
    echo "  4. View documentation: ./neuralsync.sh docs"
    echo
    log_info "For help and support, visit: https://github.com/neuralsync/neuralsync"
}

# ---- Help and Usage ----------------------------------------------------------
show_help() {
    cat <<EOF
NeuralSync Community Edition v${NEURALSYNC_VERSION}

USAGE:
    $0 <command> [options]

COMMANDS:
    install         Install NeuralSync and all dependencies
    start           Start all NeuralSync services
    stop            Stop all NeuralSync services
    restart         Restart all NeuralSync services
    status          Check system status and health
    logs [service]  Show logs (optionally for specific service)
    setup-keys      Interactive API key configuration
    upgrade         Upgrade to the latest version
    docs            Open documentation
    help            Show this help message

EXAMPLES:
    $0 install           # Install NeuralSync
    $0 start             # Start all services
    $0 logs api          # Show API service logs
    $0 status            # Check system health

SERVICES:
    postgres        PostgreSQL database with pgvector
    qdrant          Vector database for semantic memory
    neo4j           Graph database for temporal relationships
    redis           Cache and session storage
    minio           Object storage for files and backups
    neuralsync-api  Core NeuralSync API service
    neuralsync-worker   Memory processing worker
    prometheus      Metrics collection
    grafana         Monitoring dashboard
    jaeger          Distributed tracing

For detailed documentation, visit:
https://github.com/neuralsync/neuralsync/docs
EOF
}

# ---- Main Command Dispatcher ------------------------------------------------
main() {
    case "${1:-help}" in
        install)
            install_neuralsync
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 5
            start_services
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        setup-keys)
            setup_api_keys
            ;;
        upgrade)
            upgrade_system
            ;;
        docs)
            log_info "Opening documentation..."
            if command -v open >/dev/null 2>&1; then
                open "https://github.com/neuralsync/neuralsync/docs"
            elif command -v xdg-open >/dev/null 2>&1; then
                xdg-open "https://github.com/neuralsync/neuralsync/docs"
            else
                echo "Documentation: https://github.com/neuralsync/neuralsync/docs"
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# ---- Script Entry Point -----------------------------------------------------
main "$@"