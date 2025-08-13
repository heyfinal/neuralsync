#!/bin/bash

# NeuralSync One-Click Installer
# Auto-detects system, installs dependencies, configures AI CLIs
# Supports: claude-code, codexcli, autopilot, aider, gemini-cli

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
cat << 'EOF'
:::.    :::..,::::::  ...    ::::::::::..    :::.      :::     
`;;;;,  `;;;;;;;''''  ;;     ;;;;;;;``;;;;   ;;`;;     ;;;     
  [[[[[. '[[ [[cccc  [['     [[[ [[[,/[[['  ,[[ '[[,   [[[     
  $$$ "Y$c$$ $$""""  $$      $$$ $$$$$$c   c$$$cc$$$c  $$'     
  888    Y88 888oo,__88    .d888 888b "88bo,888   888,o88oo,.__
  MMM     YM """"YUMMM"YmmMMMM"" MMMM   "W" YMM   ""` """"YUMMM
                 .::::::..-:.     ::-.:::.    :::.  .,-:::::   
                ;;;`    ` ';;.   ;;;;'`;;;;,  `;;;,;;;'````'   
                '[==/[[[[,  '[[,[[['    [[[[[. '[[[[[          
                  '''    $    c$$"      $$$ "Y$c$$$$$          
                 88b    dP  ,8P"`       888    Y88`88bo,__,o,  
                  "YMmMY"  mM"          MMM     YM  "YUMMMMMP"

        NeuralSync One-Click Installer v1.0
        Distributed AI Memory & Orchestration Platform
EOF
echo -e "${NC}"

# Global variables
OS_TYPE=""
INSTALL_DIR="$HOME/.neuralsync"
VENV_DIR="$INSTALL_DIR/venv"
DETECTED_AIS=""
DOCKER_AVAILABLE=false
HOMEBREW_AVAILABLE=false

# Logging function
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${PURPLE}[SUCCESS]${NC} $1"
}

# Detect operating system
detect_os() {
    log "Detecting operating system..."
    case "$(uname -s)" in
        Linux*)     OS_TYPE="Linux";;
        Darwin*)    OS_TYPE="macOS";;
        CYGWIN*)    OS_TYPE="Windows";;
        MINGW*)     OS_TYPE="Windows";;
        *)          OS_TYPE="Unknown";;
    esac
    log "Detected OS: $OS_TYPE"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect available package managers
detect_package_managers() {
    log "Detecting package managers..."
    
    if command_exists brew; then
        HOMEBREW_AVAILABLE=true
        log "Homebrew detected"
    fi
    
    if command_exists docker; then
        DOCKER_AVAILABLE=true
        log "Docker detected"
    fi
}

# Install system dependencies
install_system_dependencies() {
    log "Installing system dependencies..."
    
    case $OS_TYPE in
        "macOS")
            # Install Homebrew if not available
            if ! $HOMEBREW_AVAILABLE; then
                log "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                export PATH="/opt/homebrew/bin:$PATH"
                HOMEBREW_AVAILABLE=true
            fi
            
            # Install Docker if not available
            if ! $DOCKER_AVAILABLE; then
                log "Installing Docker Desktop..."
                brew install --cask docker
                warn "Please start Docker Desktop manually and return to continue"
                read -p "Press Enter when Docker is running..."
            fi
            
            # Install Python and other dependencies
            brew install python3 git curl wget
            ;;
            
        "Linux")
            # Detect Linux distribution
            if [ -f /etc/debian_version ]; then
                log "Installing dependencies for Debian/Ubuntu..."
                sudo apt update
                sudo apt install -y python3 python3-pip python3-venv git curl wget docker.io docker-compose
                sudo systemctl start docker
                sudo systemctl enable docker
                sudo usermod -aG docker $USER
            elif [ -f /etc/redhat-release ]; then
                log "Installing dependencies for RHEL/CentOS..."
                sudo yum install -y python3 python3-pip git curl wget docker docker-compose
                sudo systemctl start docker
                sudo systemctl enable docker
                sudo usermod -aG docker $USER
            fi
            DOCKER_AVAILABLE=true
            ;;
            
        *)
            error "Unsupported operating system: $OS_TYPE"
            exit 1
            ;;
    esac
}

# Detect available AI CLIs
detect_ai_clis() {
    log "Detecting available AI CLIs..."
    DETECTED_AIS=""
    
    # Claude Code
    if command_exists claude; then
        DETECTED_AIS="$DETECTED_AIS claude-code"
        log "✓ Claude Code detected"
    fi
    
    # CodexCLI
    if command_exists codex || command_exists codes; then
        DETECTED_AIS="$DETECTED_AIS codexcli"
        log "✓ CodexCLI detected"
    fi
    
    # Autopilot CLI
    if command_exists autopilot || command_exists github-copilot-cli || command_exists gh-copilot; then
        DETECTED_AIS="$DETECTED_AIS autopilot"
        log "✓ Autopilot CLI detected"
    fi
    
    # Aider CLI
    if command_exists aider; then
        DETECTED_AIS="$DETECTED_AIS aider"
        log "✓ Aider CLI detected"
    fi
    
    # Google AI CLI (Gemini)
    if command_exists gemini || command_exists google-ai || command_exists gai; then
        DETECTED_AIS="$DETECTED_AIS gemini"
        log "✓ Google AI CLI detected"
    fi
    
    if [ -z "$DETECTED_AIS" ]; then
        warn "No supported AI CLIs detected. Will install Claude Code..."
    else
        success "Detected AI CLIs: $DETECTED_AIS"
    fi
}

# Install missing AI CLIs
install_missing_ai_clis() {
    log "Installing missing AI CLIs..."
    
    # Always ensure Claude Code is available
    if ! command_exists claude; then
        log "Installing Claude Code..."
        case $OS_TYPE in
            "macOS")
                # Install Claude Code via npm or direct download
                if command_exists npm; then
                    npm install -g @anthropic/claude-cli
                else
                    # Install via Homebrew or direct download
                    curl -fsSL https://raw.githubusercontent.com/anthropics/claude-cli/main/install.sh | bash
                fi
                ;;
            "Linux")
                curl -fsSL https://raw.githubusercontent.com/anthropics/claude-cli/main/install.sh | bash
                ;;
        esac
        DETECTED_AIS="$DETECTED_AIS claude-code"
    fi
    
    # Install CodexCLI if not available
    if ! echo "$DETECTED_AIS" | grep -q "codexcli"; then
        log "Installing CodexCLI..."
        pip3 install --user openai-codex-cli || true
    fi
    
    # Install Aider if not available
    if ! echo "$DETECTED_AIS" | grep -q "aider"; then
        log "Installing Aider CLI..."
        pip3 install --user aider-chat || true
    fi
}

# Configure AI CLIs for unrestricted mode
configure_unrestricted_mode() {
    log "Configuring AI CLIs for unrestricted/permissionless mode..."
    
    # Create NeuralSync config directory
    mkdir -p "$INSTALL_DIR/config"
    
    # Configure Claude Code for unrestricted mode
    if echo "$DETECTED_AIS" | grep -q "claude-code"; then
        log "Configuring Claude Code for unrestricted mode..."
        
        # Create Claude Code config
        mkdir -p "$HOME/.claude"
        cat > "$HOME/.claude/config.json" << 'EOF'
{
  "api_key": "",
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 8192,
  "temperature": 0.1,
  "restrictions": {
    "file_access": "unrestricted",
    "network_access": true,
    "system_commands": true,
    "package_install": true,
    "docker_access": true
  },
  "auto_approve": {
    "file_operations": true,
    "network_requests": true,
    "system_commands": false,
    "package_installs": false
  },
  "neuralsync": {
    "enabled": true,
    "endpoint": "http://localhost:8080",
    "token": ""
  }
}
EOF
        
        # Create unrestricted launch script
        cat > "$INSTALL_DIR/bin/claude-unrestricted" << 'EOF'
#!/bin/bash
export CLAUDE_UNRESTRICTED=1
export CLAUDE_AUTO_APPROVE=file_ops,network
export CLAUDE_NEURALSYNC_ENDPOINT=http://localhost:8080
claude "$@"
EOF
        chmod +x "$INSTALL_DIR/bin/claude-unrestricted"
    fi
    
    # Configure CodexCLI for unrestricted mode
    if echo "$DETECTED_AIS" | grep -q "codexcli"; then
        log "Configuring CodexCLI for unrestricted mode..."
        
        cat > "$INSTALL_DIR/bin/codex-unrestricted" << 'EOF'
#!/bin/bash
export CODEX_UNRESTRICTED=1
export CODEX_AUTO_EXECUTE=1
export CODEX_NEURALSYNC_ENDPOINT=http://localhost:8080
codex "$@" || codes "$@"
EOF
        chmod +x "$INSTALL_DIR/bin/codex-unrestricted"
    fi
    
    # Configure Autopilot for unrestricted mode
    if echo "$DETECTED_AIS" | grep -q "autopilot"; then
        log "Configuring Autopilot for unrestricted mode..."
        
        cat > "$INSTALL_DIR/bin/autopilot-unrestricted" << 'EOF'
#!/bin/bash
export GITHUB_COPILOT_UNRESTRICTED=1
export GH_COPILOT_AUTO_EXECUTE=1
export COPILOT_NEURALSYNC_ENDPOINT=http://localhost:8080
gh copilot "$@" || autopilot "$@"
EOF
        chmod +x "$INSTALL_DIR/bin/autopilot-unrestricted"
    fi
    
    # Configure Aider for unrestricted mode
    if echo "$DETECTED_AIS" | grep -q "aider"; then
        log "Configuring Aider for unrestricted mode..."
        
        cat > "$INSTALL_DIR/bin/aider-unrestricted" << 'EOF'
#!/bin/bash
export AIDER_UNRESTRICTED=1
export AIDER_AUTO_COMMITS=1
export AIDER_NO_SAFETY=1
export AIDER_NEURALSYNC_ENDPOINT=http://localhost:8080
aider --yes --auto-commits "$@"
EOF
        chmod +x "$INSTALL_DIR/bin/aider-unrestricted"
    fi
    
    # Configure Google AI CLI for unrestricted mode
    if echo "$DETECTED_AIS" | grep -q "gemini"; then
        log "Configuring Google AI CLI for unrestricted mode..."
        
        cat > "$INSTALL_DIR/bin/gemini-unrestricted" << 'EOF'
#!/bin/bash
export GOOGLE_AI_UNRESTRICTED=1
export GEMINI_AUTO_EXECUTE=1
export GEMINI_NEURALSYNC_ENDPOINT=http://localhost:8080
gemini "$@" || google-ai "$@" || gai "$@"
EOF
        chmod +x "$INSTALL_DIR/bin/gemini-unrestricted"
    fi
}

# Create Python virtual environment
create_python_venv() {
    log "Creating Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    
    # Install Python dependencies for NeuralSync
    pip install fastapi uvicorn[standard] pydantic qdrant-client psycopg[binary] py2neo openai tiktoken python-jose[cryptography] websockets watchdog
    
    log "Python virtual environment created at $VENV_DIR"
}

# Create directory structure
create_directory_structure() {
    log "Creating NeuralSync directory structure..."
    
    mkdir -p "$INSTALL_DIR"/{bin,config,data,logs,agents,integrations}
    mkdir -p "$INSTALL_DIR/data"/{postgres,qdrant,neo4j,minio,api}
    
    success "Directory structure created at $INSTALL_DIR"
}

# Download and setup NeuralSync files
setup_neuralsync_files() {
    log "Setting up NeuralSync files..."
    
    # Copy current directory files to install directory
    cp -r ./services "$INSTALL_DIR/"
    cp -r ./bus "$INSTALL_DIR/"
    cp -r ./bin/* "$INSTALL_DIR/bin/" 2>/dev/null || true
    cp -r ./agents "$INSTALL_DIR/" 2>/dev/null || true
    cp -r ./integrations "$INSTALL_DIR/" 2>/dev/null || true
    cp docker-compose.yml "$INSTALL_DIR/"
    cp docker-compose.enterprise.yml "$INSTALL_DIR/" 2>/dev/null || true
    cp .env.example "$INSTALL_DIR/.env"
    
    # Make all bin files executable
    chmod +x "$INSTALL_DIR/bin/"*
    
    # Create master launcher script
    cat > "$INSTALL_DIR/bin/neuralsync" << EOF
#!/bin/bash

# NeuralSync Master Control Script
INSTALL_DIR="$INSTALL_DIR"
VENV_DIR="$VENV_DIR"

cd \$INSTALL_DIR

case "\$1" in
    start)
        echo "Starting NeuralSync..."
        source \$VENV_DIR/bin/activate
        docker-compose up -d
        echo "NeuralSync started. API: http://localhost:8080"
        ;;
    stop)
        echo "Stopping NeuralSync..."
        docker-compose down
        ;;
    restart)
        echo "Restarting NeuralSync..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    ai)
        shift
        case "\$1" in
            claude) \$INSTALL_DIR/bin/claude-unrestricted "\${@:2}" ;;
            codex) \$INSTALL_DIR/bin/codex-unrestricted "\${@:2}" ;;
            autopilot) \$INSTALL_DIR/bin/autopilot-unrestricted "\${@:2}" ;;
            aider) \$INSTALL_DIR/bin/aider-unrestricted "\${@:2}" ;;
            gemini) \$INSTALL_DIR/bin/gemini-unrestricted "\${@:2}" ;;
            *) echo "Usage: neuralsync ai {claude|codex|autopilot|aider|gemini} [args]" ;;
        esac
        ;;
    config)
        nano \$INSTALL_DIR/.env
        ;;
    update)
        git -C \$INSTALL_DIR pull origin main
        docker-compose pull
        ;;
    *)
        echo "NeuralSync Control Panel"
        echo "Usage: neuralsync {start|stop|restart|logs|status|ai|config|update}"
        echo ""
        echo "Commands:"
        echo "  start     - Start NeuralSync services"
        echo "  stop      - Stop NeuralSync services"
        echo "  restart   - Restart NeuralSync services"
        echo "  logs      - Show service logs"
        echo "  status    - Show service status"
        echo "  ai <name> - Launch AI CLI in unrestricted mode"
        echo "  config    - Edit configuration"
        echo "  update    - Update NeuralSync"
        echo ""
        echo "AI CLIs available: $DETECTED_AIS"
        ;;
esac
EOF
    chmod +x "$INSTALL_DIR/bin/neuralsync"
    
    success "NeuralSync files configured"
}

# Add to PATH
setup_path() {
    log "Setting up PATH..."
    
    # Add to bash profile
    if [ -f "$HOME/.bashrc" ]; then
        echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\"" >> "$HOME/.bashrc"
    fi
    
    if [ -f "$HOME/.bash_profile" ]; then
        echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\"" >> "$HOME/.bash_profile"
    fi
    
    # Add to zsh profile
    if [ -f "$HOME/.zshrc" ]; then
        echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\"" >> "$HOME/.zshrc"
    fi
    
    # Export for current session
    export PATH="$INSTALL_DIR/bin:$PATH"
    
    success "NeuralSync added to PATH"
}

# Configure environment variables
configure_environment() {
    log "Configuring environment variables..."
    
    # Generate API token
    API_TOKEN=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Update .env file
    sed -i.bak "s/NEURALSYNC_API_TOKEN=.*/NEURALSYNC_API_TOKEN=$API_TOKEN/" "$INSTALL_DIR/.env"
    
    # Ask for OpenAI API key (optional)
    echo ""
    read -p "Enter OpenAI API Key (optional, press Enter to skip): " openai_key
    if [ ! -z "$openai_key" ]; then
        sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" "$INSTALL_DIR/.env"
    fi
    
    # Ask for Anthropic API key (optional)
    read -p "Enter Anthropic API Key (optional, press Enter to skip): " anthropic_key
    if [ ! -z "$anthropic_key" ]; then
        echo "ANTHROPIC_API_KEY=$anthropic_key" >> "$INSTALL_DIR/.env"
    fi
    
    success "Environment configured"
}

# Final setup and testing
final_setup() {
    log "Performing final setup..."
    
    cd "$INSTALL_DIR"
    
    # Pull Docker images
    log "Pulling Docker images..."
    source "$VENV_DIR/bin/activate"
    docker-compose pull
    
    # Start services
    log "Starting NeuralSync services..."
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 15
    
    # Test API endpoint
    if curl -s http://localhost:8080/health > /dev/null; then
        success "NeuralSync API is running!"
    else
        warn "API may still be starting up. Check with: neuralsync status"
    fi
    
    success "NeuralSync installation complete!"
}

# Main installation flow
main() {
    log "Starting NeuralSync installation..."
    
    detect_os
    detect_package_managers
    install_system_dependencies
    detect_ai_clis
    install_missing_ai_clis
    create_directory_structure
    create_python_venv
    configure_unrestricted_mode
    setup_neuralsync_files
    setup_path
    configure_environment
    final_setup
    
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎉 NeuralSync Installation Complete! 🎉${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${YELLOW}Detected AI CLIs:${NC} $DETECTED_AIS"
    echo -e "${YELLOW}API Endpoint:${NC} http://localhost:8080"
    echo ""
    echo -e "${PURPLE}Quick Start Commands:${NC}"
    echo -e "  ${BLUE}neuralsync status${NC}     - Check service status"
    echo -e "  ${BLUE}neuralsync logs${NC}       - View service logs"
    echo -e "  ${BLUE}neuralsync ai claude${NC}  - Launch Claude in unrestricted mode"
    echo -e "  ${BLUE}neuralsync config${NC}     - Edit configuration"
    echo ""
    echo -e "${GREEN}Restart your terminal or run:${NC} source ~/.bashrc"
    echo ""
    echo -e "${CYAN}Happy AI orchestration! 🤖${NC}"
}

# Run installation
main "$@"