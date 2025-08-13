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
USER_NAME=""
NAS_MOUNT_POINT=""
NAS_IP=""
NAS_USERNAME=""
NAS_PASSWORD=""
SCAN_AI_CONFIGS=false
AI_CONFIG_FILES=""
NEURALSYNC_ADMIN_USER=""
NEURALSYNC_ADMIN_PASS=""

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

# Get user information and preferences
get_user_preferences() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}🎯 NeuralSync Personal Configuration${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Get user's name
    echo -e "${BLUE}👋 Personal Information${NC}"
    echo "NeuralSync AIs will address you personally by name for better interaction."
    read -p "What's your name? (e.g., Daniel, Sarah): " USER_NAME
    if [ -z "$USER_NAME" ]; then
        USER_NAME="User"
    fi
    log "Hello $USER_NAME! Setting up personalized AI experience..."
    echo ""
    
    # NeuralSync admin credentials
    echo -e "${BLUE}🔐 Admin Account Setup${NC}"
    echo "Create admin credentials for NeuralSync configuration and memory access."
    read -p "Choose admin username (default: admin): " admin_user
    NEURALSYNC_ADMIN_USER=${admin_user:-admin}
    
    while true; do
        read -s -p "Create admin password: " admin_pass1
        echo ""
        read -s -p "Confirm admin password: " admin_pass2
        echo ""
        if [ "$admin_pass1" = "$admin_pass2" ]; then
            NEURALSYNC_ADMIN_PASS="$admin_pass1"
            break
        else
            error "Passwords don't match. Please try again."
        fi
    done
    success "Admin account configured for $NEURALSYNC_ADMIN_USER"
    echo ""
    
    # NAS Configuration
    echo -e "${BLUE}💾 Network Storage Configuration${NC}"
    echo "NeuralSync can use network storage for cold memory archival and backup."
    echo ""
    read -p "Do you want to configure NAS storage? (y/N): " configure_nas
    if [[ $configure_nas =~ ^[Yy]$ ]]; then
        echo ""
        echo "Choose NAS configuration method:"
        echo "1) Direct mount point (e.g., /Volumes/MyNAS, /mnt/nas)"
        echo "2) IP address with credentials"
        read -p "Enter choice (1-2): " nas_choice
        
        case $nas_choice in
            1)
                read -p "Enter NAS mount point path: " NAS_MOUNT_POINT
                if [ ! -d "$NAS_MOUNT_POINT" ]; then
                    warn "Mount point $NAS_MOUNT_POINT does not exist. You can configure this later."
                else
                    success "NAS mount point configured: $NAS_MOUNT_POINT"
                fi
                ;;
            2)
                read -p "Enter NAS IP address: " NAS_IP
                read -p "Enter NAS username: " NAS_USERNAME
                read -s -p "Enter NAS password: " NAS_PASSWORD
                echo ""
                success "NAS credentials configured for $NAS_IP"
                ;;
        esac
    else
        log "Skipping NAS configuration (can be added later)"
    fi
    echo ""
    
    # AI Config File Scanning
    echo -e "${BLUE}🔍 AI Configuration Discovery${NC}"
    echo "NeuralSync can scan your system for existing AI configuration files"
    echo "(like .claude.md, .cursor-rules, .aider.conf.yml, etc.) to create"
    echo "a comprehensive base memory and prime directive system."
    echo ""
    echo -e "${YELLOW}This will scan common locations like:${NC}"
    echo "  • ~/.claude.md, ~/.claude/"
    echo "  • ~/.cursor/, .cursor-rules"
    echo "  • ~/.aider.conf.yml"
    echo "  • ~/.config/ directories"
    echo "  • Project-specific AI config files"
    echo ""
    read -p "Scan and compile AI configuration files? (y/N): " scan_consent
    if [[ $scan_consent =~ ^[Yy]$ ]]; then
        SCAN_AI_CONFIGS=true
        log "Will scan for AI configuration files"
    else
        log "Skipping AI config file scanning"
    fi
    echo ""
}

# Scan for existing AI configuration files
scan_ai_configurations() {
    if [ "$SCAN_AI_CONFIGS" = false ]; then
        return
    fi
    
    log "Scanning filesystem for AI configuration files..."
    
    # Define common AI config file patterns
    local config_patterns=(
        "$HOME/.claude.md"
        "$HOME/.claude/CLAUDE.md"
        "$HOME/.claude/config.json"
        "$HOME/.cursor-rules"
        "$HOME/.cursor/rules.md"
        "$HOME/.aider.conf.yml"
        "$HOME/.aider/config.yml"
        "$HOME/.config/cursor/"
        "$HOME/.config/aider/"
        "$HOME/.config/claude/"
        "$HOME/.codeium/config.json"
        "$HOME/.copilot/config.yml"
        "$HOME/.chatgpt/config.json"
        "$HOME/CLAUDE.md"
        "$HOME/AI_INSTRUCTIONS.md"
        "$HOME/PROJECT_INSTRUCTIONS.md"
        "$HOME/.ai/"
        "$HOME/.llm/"
    )
    
    # Find files in common project locations
    local project_patterns=(
        "CLAUDE.md"
        ".claude.md" 
        ".cursor-rules"
        ".aider.conf.yml"
        "AI_INSTRUCTIONS.md"
        "PROJECT_CONTEXT.md"
        ".ai/instructions.md"
        ".github/ai-instructions.md"
    )
    
    AI_CONFIG_FILES=""
    
    # Scan home directory patterns
    for pattern in "${config_patterns[@]}"; do
        if [ -f "$pattern" ] || [ -d "$pattern" ]; then
            AI_CONFIG_FILES="$AI_CONFIG_FILES\n$pattern"
            log "Found: $pattern"
        fi
    done
    
    # Scan common development directories for project-specific configs
    local dev_dirs=("$HOME/Desktop" "$HOME/Documents" "$HOME/Projects" "$HOME/Code" "$HOME/Development")
    for dev_dir in "${dev_dirs[@]}"; do
        if [ -d "$dev_dir" ]; then
            for pattern in "${project_patterns[@]}"; do
                find "$dev_dir" -name "$pattern" -type f 2>/dev/null | while read -r file; do
                    AI_CONFIG_FILES="$AI_CONFIG_FILES\n$file"
                    log "Found project config: $file"
                done
            done
        fi
    done
    
    # Also check if we're in a git repository with AI configs
    local current_dir="$PWD"
    while [ "$current_dir" != "/" ]; do
        if [ -d "$current_dir/.git" ]; then
            for pattern in "${project_patterns[@]}"; do
                if [ -f "$current_dir/$pattern" ]; then
                    AI_CONFIG_FILES="$AI_CONFIG_FILES\n$current_dir/$pattern"
                    log "Found git project config: $current_dir/$pattern"
                fi
            done
            break
        fi
        current_dir="$(dirname "$current_dir")"
    done
    
    if [ ! -z "$AI_CONFIG_FILES" ]; then
        local count=$(echo -e "$AI_CONFIG_FILES" | grep -c .)
        success "Found $count AI configuration files"
    else
        warn "No AI configuration files found"
    fi
}

# Compile AI configurations into base memory
compile_base_memory() {
    if [ "$SCAN_AI_CONFIGS" = false ] || [ -z "$AI_CONFIG_FILES" ]; then
        return
    fi
    
    log "Compiling AI configurations into base memory system..."
    
    local base_memory_file="$INSTALL_DIR/config/base_memory.md"
    local prime_directive_file="$INSTALL_DIR/config/prime_directive.md"
    
    # Create base memory file
    cat > "$base_memory_file" << EOF
# NeuralSync Base Memory System
# Compiled from user's existing AI configurations
# Generated: $(date)
# User: $USER_NAME

## User Profile
**Name**: $USER_NAME
**System**: $(uname -a)
**Install Date**: $(date)
**NAS Configuration**: ${NAS_MOUNT_POINT:-$NAS_IP}

## Compiled AI Configurations

EOF
    
    # Create prime directive file
    cat > "$prime_directive_file" << EOF
# NeuralSync Prime Directive
# Core instructions compiled from user's AI configurations
# User: $USER_NAME

## Core Identity
You are part of the NeuralSync AI orchestration platform serving $USER_NAME.
You have access to persistent memory, cross-AI communication, and comprehensive context.

## User Preferences (Compiled from existing configs)

EOF
    
    # Process each found configuration file
    echo -e "$AI_CONFIG_FILES" | while read -r config_file; do
        if [ -f "$config_file" ] && [ -s "$config_file" ]; then
            log "Processing: $config_file"
            
            echo "### Configuration from: \`$config_file\`" >> "$base_memory_file"
            echo "" >> "$base_memory_file"
            echo "\`\`\`" >> "$base_memory_file"
            cat "$config_file" >> "$base_memory_file"
            echo "" >> "$base_memory_file"
            echo "\`\`\`" >> "$base_memory_file"
            echo "" >> "$base_memory_file"
            
            # Extract key instructions for prime directive
            if grep -qi "instruction\|rule\|directive\|guideline\|preference" "$config_file"; then
                echo "#### From \`$(basename "$config_file")\`:" >> "$prime_directive_file"
                grep -i "instruction\|rule\|directive\|guideline\|preference" "$config_file" | head -10 >> "$prime_directive_file"
                echo "" >> "$prime_directive_file"
            fi
        fi
    done
    
    # Add NeuralSync-specific directives
    cat >> "$prime_directive_file" << EOF

## NeuralSync Core Directives

1. **Personal Address**: Always address the user as "$USER_NAME"
2. **Memory Integration**: Utilize persistent memory for context continuity
3. **Cross-AI Collaboration**: Coordinate with other AI agents when beneficial
4. **User Autonomy**: Respect user preferences from compiled configurations
5. **Context Awareness**: Maintain awareness of project context and user goals

## Collaboration Guidelines

When working with other AIs in the NeuralSync network:
- Share relevant context through the memory system
- Avoid duplicate work by checking existing memory
- Coordinate task delegation based on AI strengths
- Maintain consistent personality and preferences for $USER_NAME

EOF
    
    success "Base memory system compiled with user configurations"
    log "Base memory: $base_memory_file"
    log "Prime directive: $prime_directive_file"
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
    
    # GPT-5 Planner (ChatBot)
    if command_exists chatgpt || command_exists gpt || command_exists openai-chat; then
        DETECTED_AIS="$DETECTED_AIS gpt5-planner"
        log "✓ GPT-5 Planner (ChatBot) detected"
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
    
    # Install GPT-5 Planner (ChatBot) if not available
    if ! echo "$DETECTED_AIS" | grep -q "gpt5-planner"; then
        log "Installing GPT-5 Planner (ChatBot)..."
        pip3 install --user chatgpt-cli || pip3 install --user openai-chatbot || true
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
    
    # Configure GPT-5 Planner (ChatBot) for unrestricted mode
    if echo "$DETECTED_AIS" | grep -q "gpt5-planner"; then
        log "Configuring GPT-5 Planner (ChatBot) for unrestricted mode..."
        
        cat > "$INSTALL_DIR/bin/gpt5-planner-unrestricted" << 'EOF'
#!/bin/bash
export CHATGPT_UNRESTRICTED=1
export GPT5_AUTO_EXECUTE=1
export GPT5_NEURALSYNC_ENDPOINT=http://localhost:8080
chatgpt "$@" || gpt "$@" || openai-chat "$@"
EOF
        chmod +x "$INSTALL_DIR/bin/gpt5-planner-unrestricted"
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

# Clone and setup NeuralSync from GitHub
clone_and_setup_neuralsync() {
    log "Cloning NeuralSync from GitHub..."
    
    # Check if we're already in a neuralsync directory or if files exist locally
    if [ -f "docker-compose.yml" ] && [ -d "services" ] && [ -d "bus" ]; then
        log "Found local NeuralSync files, using existing installation..."
        setup_local_files
    else
        log "Cloning from GitHub repository..."
        
        # Create temporary directory for cloning
        local temp_dir="/tmp/neuralsync-install-$$"
        git clone https://github.com/heyfinal/neuralsync.git "$temp_dir"
        
        if [ $? -eq 0 ]; then
            success "Repository cloned successfully"
            cd "$temp_dir"
            setup_local_files
            
            # Clean up temporary directory after copying
            cd "$HOME"
            rm -rf "$temp_dir"
        else
            error "Failed to clone repository. Check your internet connection."
            exit 1
        fi
    fi
}

# Setup files from local directory (whether cloned or existing)
setup_local_files() {
    log "Setting up NeuralSync files..."
    
    # Copy current directory files to install directory
    cp -r ./services "$INSTALL_DIR/" 2>/dev/null || true
    cp -r ./bus "$INSTALL_DIR/" 2>/dev/null || true
    cp -r ./bin/* "$INSTALL_DIR/bin/" 2>/dev/null || true
    cp -r ./agents "$INSTALL_DIR/" 2>/dev/null || true
    cp -r ./integrations "$INSTALL_DIR/" 2>/dev/null || true
    cp docker-compose.yml "$INSTALL_DIR/" 2>/dev/null || true
    cp docker-compose.enterprise.yml "$INSTALL_DIR/" 2>/dev/null || true
    cp .env.example "$INSTALL_DIR/.env" 2>/dev/null || true
    
    # Make all bin files executable
    chmod +x "$INSTALL_DIR/bin/"* 2>/dev/null || true
    
    # Create master launcher script with auto-launch capabilities
    create_master_launcher_script
    
    success "NeuralSync files configured"
}

# Create comprehensive master launcher script
create_master_launcher_script() {
    log "Creating NeuralSync master control script..."
    
    cat > "$INSTALL_DIR/bin/neuralsync" << 'EOF'
#!/bin/bash

# NeuralSync Master Control Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$INSTALL_DIR/venv"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cd "$INSTALL_DIR"

case "$1" in
    start)
        echo -e "${BLUE}Starting NeuralSync...${NC}"
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        docker-compose up -d
        
        # Wait for services to be ready
        log "Waiting for services to start..."
        sleep 15
        
        # Verify API is running
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ NeuralSync started successfully!${NC}"
            echo -e "${BLUE}API: http://localhost:8080${NC}"
            echo -e "${BLUE}Memory Dashboard: http://localhost:6333/dashboard${NC}"
            echo -e "${BLUE}Graph Explorer: http://localhost:7474${NC}"
        else
            warn "Services may still be starting. Check status with: neuralsync status"
        fi
        ;;
        
    autostart)
        echo -e "${BLUE}Auto-starting NeuralSync with AI agents...${NC}"
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        docker-compose up -d
        
        # Wait for services
        log "Waiting for core services..."
        sleep 20
        
        # Auto-launch detected AI agents in background
        log "Auto-launching AI agents..."
        
        # Launch Claude Code if available
        if command -v claude >/dev/null 2>&1; then
            log "Starting Claude Code agent..."
            nohup "$INSTALL_DIR/bin/claude-unrestricted" >/dev/null 2>&1 &
            echo $! > "$INSTALL_DIR/data/claude.pid"
        fi
        
        # Launch CodexCLI if available
        if command -v codex >/dev/null 2>&1 || command -v codes >/dev/null 2>&1; then
            log "Starting CodexCLI agent..."
            nohup "$INSTALL_DIR/bin/codex-unrestricted" >/dev/null 2>&1 &
            echo $! > "$INSTALL_DIR/data/codex.pid"
        fi
        
        # Launch Aider if available
        if command -v aider >/dev/null 2>&1; then
            log "Starting Aider agent..."
            nohup "$INSTALL_DIR/bin/aider-unrestricted" >/dev/null 2>&1 &
            echo $! > "$INSTALL_DIR/data/aider.pid"
        fi
        
        # Launch GPT-5 Planner (ChatBot) if available
        if command -v chatgpt >/dev/null 2>&1 || command -v gpt >/dev/null 2>&1; then
            log "Starting GPT-5 Planner (ChatBot)..."
            nohup "$INSTALL_DIR/bin/gpt5-planner-unrestricted" >/dev/null 2>&1 &
            echo $! > "$INSTALL_DIR/data/gpt5-planner.pid"
        fi
        
        echo -e "${GREEN}✅ NeuralSync auto-started with AI agents!${NC}"
        "$0" status
        ;;
        
    stop)
        echo -e "${YELLOW}Stopping NeuralSync...${NC}"
        docker-compose down
        
        # Stop AI agent processes
        for pidfile in "$INSTALL_DIR/data/"*.pid; do
            if [ -f "$pidfile" ]; then
                pid=$(cat "$pidfile" 2>/dev/null)
                if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                    log "Stopping AI agent (PID: $pid)"
                    kill "$pid" 2>/dev/null || true
                fi
                rm -f "$pidfile"
            fi
        done
        
        echo -e "${GREEN}✅ NeuralSync stopped${NC}"
        ;;
        
    restart)
        echo -e "${BLUE}Restarting NeuralSync...${NC}"
        "$0" stop
        sleep 5
        "$0" start
        ;;
        
    logs)
        if [ ! -z "$2" ]; then
            docker-compose logs -f "$2"
        else
            docker-compose logs -f
        fi
        ;;
        
    status)
        echo -e "${BLUE}NeuralSync Service Status:${NC}"
        docker-compose ps
        echo ""
        
        # Check API health
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ API: Running (http://localhost:8080)${NC}"
        else
            echo -e "${RED}❌ API: Not responding${NC}"
        fi
        
        # Check AI agent processes
        echo -e "${BLUE}AI Agent Status:${NC}"
        for pidfile in "$INSTALL_DIR/data/"*.pid; do
            if [ -f "$pidfile" ]; then
                agent_name=$(basename "$pidfile" .pid)
                pid=$(cat "$pidfile" 2>/dev/null)
                if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                    echo -e "${GREEN}✅ $agent_name: Running (PID: $pid)${NC}"
                else
                    echo -e "${RED}❌ $agent_name: Not running${NC}"
                    rm -f "$pidfile"
                fi
            fi
        done
        ;;
        
    health)
        # Comprehensive health check
        echo -e "${BLUE}NeuralSync Health Check:${NC}"
        
        # Check Docker
        if ! docker ps >/dev/null 2>&1; then
            echo -e "${RED}❌ Docker: Not running${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Docker: Running${NC}"
        
        # Check services
        local services=("postgres" "qdrant" "neo4j" "api" "worker")
        for service in "${services[@]}"; do
            if docker-compose ps | grep -q "$service.*Up"; then
                echo -e "${GREEN}✅ $service: Running${NC}"
            else
                echo -e "${RED}❌ $service: Not running${NC}"
            fi
        done
        
        # Check API endpoint
        if curl -s http://localhost:8080/health | grep -q "ok"; then
            echo -e "${GREEN}✅ API Health: OK${NC}"
        else
            echo -e "${RED}❌ API Health: Failed${NC}"
        fi
        ;;
        
    ai)
        shift
        case "$1" in
            claude) 
                log "Launching Claude Code in unrestricted mode..."
                exec "$INSTALL_DIR/bin/claude-unrestricted" "${@:2}"
                ;;
            codex) 
                log "Launching CodexCLI in unrestricted mode..."
                exec "$INSTALL_DIR/bin/codex-unrestricted" "${@:2}"
                ;;
            autopilot) 
                log "Launching Autopilot in unrestricted mode..."
                exec "$INSTALL_DIR/bin/autopilot-unrestricted" "${@:2}"
                ;;
            aider) 
                log "Launching Aider in unrestricted mode..."
                exec "$INSTALL_DIR/bin/aider-unrestricted" "${@:2}"
                ;;
            gemini) 
                log "Launching Gemini in unrestricted mode..."
                exec "$INSTALL_DIR/bin/gemini-unrestricted" "${@:2}"
                ;;
            gpt5-planner|chatgpt|planner)
                log "Launching GPT-5 Planner (ChatBot) in unrestricted mode..."
                exec "$INSTALL_DIR/bin/gpt5-planner-unrestricted" "${@:2}"
                ;;
            list)
                echo -e "${BLUE}Available AI CLIs:${NC}"
                command -v claude >/dev/null 2>&1 && echo -e "${GREEN}✅ claude (Claude Code)${NC}" || echo -e "${RED}❌ claude${NC}"
                (command -v codex >/dev/null 2>&1 || command -v codes >/dev/null 2>&1) && echo -e "${GREEN}✅ codex (CodexCLI)${NC}" || echo -e "${RED}❌ codex${NC}"
                command -v autopilot >/dev/null 2>&1 && echo -e "${GREEN}✅ autopilot (GitHub Copilot)${NC}" || echo -e "${RED}❌ autopilot${NC}"
                command -v aider >/dev/null 2>&1 && echo -e "${GREEN}✅ aider (AI Pair Programming)${NC}" || echo -e "${RED}❌ aider${NC}"
                (command -v gemini >/dev/null 2>&1 || command -v google-ai >/dev/null 2>&1) && echo -e "${GREEN}✅ gemini (Google AI)${NC}" || echo -e "${RED}❌ gemini${NC}"
                (command -v chatgpt >/dev/null 2>&1 || command -v gpt >/dev/null 2>&1) && echo -e "${GREEN}✅ gpt5-planner (ChatBot)${NC}" || echo -e "${RED}❌ gpt5-planner${NC}"
                ;;
            *) 
                echo "Usage: neuralsync ai {claude|codex|autopilot|aider|gemini|gpt5-planner|list} [args]"
                echo "Use 'neuralsync ai list' to see available AI CLIs"
                ;;
        esac
        ;;
        
    config)
        if command -v nano >/dev/null 2>&1; then
            nano "$INSTALL_DIR/.env"
        elif command -v vim >/dev/null 2>&1; then
            vim "$INSTALL_DIR/.env"
        else
            echo "Opening config file with default editor..."
            "${EDITOR:-vi}" "$INSTALL_DIR/.env"
        fi
        ;;
        
    update)
        log "Updating NeuralSync..."
        
        # Pull latest Docker images
        docker-compose pull
        
        # Backup current config
        cp "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.backup.$(date +%s)"
        
        # Try to update from git if in a git repo
        if [ -d "$INSTALL_DIR/.git" ]; then
            git -C "$INSTALL_DIR" pull origin main
        else
            warn "Not a git repository. Manual update required."
        fi
        
        log "Update complete. Restart services with: neuralsync restart"
        ;;
        
    install-cli)
        # Install missing AI CLIs
        shift
        case "$1" in
            claude)
                log "Installing Claude Code..."
                if command -v npm >/dev/null 2>&1; then
                    npm install -g @anthropic/claude-cli
                else
                    curl -fsSL https://raw.githubusercontent.com/anthropics/claude-cli/main/install.sh | bash
                fi
                ;;
            codex)
                log "Installing CodexCLI..."
                pip3 install --user openai-codex-cli
                ;;
            aider)
                log "Installing Aider..."
                pip3 install --user aider-chat
                ;;
            gpt5-planner|chatgpt)
                log "Installing GPT-5 Planner (ChatBot)..."
                pip3 install --user chatgpt-cli
                ;;
            *)
                echo "Usage: neuralsync install-cli {claude|codex|aider|gpt5-planner}"
                ;;
        esac
        ;;
        
    *)
        echo -e "${BLUE}NeuralSync Control Panel${NC}"
        echo "Usage: neuralsync {command} [options]"
        echo ""
        echo -e "${YELLOW}Core Commands:${NC}"
        echo "  start       - Start NeuralSync services"
        echo "  autostart   - Start services + auto-launch AI agents"
        echo "  stop        - Stop NeuralSync services and AI agents"
        echo "  restart     - Restart NeuralSync services"
        echo "  status      - Show service and AI agent status"
        echo "  health      - Comprehensive health check"
        echo ""
        echo -e "${YELLOW}AI Integration:${NC}"
        echo "  ai <name>   - Launch AI CLI in unrestricted mode"
        echo "  ai list     - Show available AI CLIs"
        echo ""
        echo -e "${YELLOW}Management:${NC}"
        echo "  logs [svc]  - Show service logs"
        echo "  config      - Edit configuration"
        echo "  update      - Update NeuralSync"
        echo "  install-cli - Install missing AI CLIs"
        echo ""
        echo -e "${YELLOW}Quick Start:${NC}"
        echo "  neuralsync autostart  # Start everything automatically"
        echo "  neuralsync ai claude  # Launch Claude in unrestricted mode"
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
    
    # Hash admin password
    ADMIN_PASS_HASH=$(echo -n "$NEURALSYNC_ADMIN_PASS" | sha256sum | awk '{print $1}' 2>/dev/null || echo -n "$NEURALSYNC_ADMIN_PASS" | shasum -a 256 | awk '{print $1}')
    
    # Update .env file with all configurations
    sed -i.bak "s/NEURALSYNC_API_TOKEN=.*/NEURALSYNC_API_TOKEN=$API_TOKEN/" "$INSTALL_DIR/.env"
    
    # Add user and admin configurations
    cat >> "$INSTALL_DIR/.env" << EOF

# User Configuration
NEURALSYNC_USER_NAME="$USER_NAME"
NEURALSYNC_ADMIN_USER="$NEURALSYNC_ADMIN_USER"
NEURALSYNC_ADMIN_PASS_HASH="$ADMIN_PASS_HASH"

# NAS Configuration
EOF
    
    if [ ! -z "$NAS_MOUNT_POINT" ]; then
        echo "NEURALSYNC_NAS_MOUNT_POINT=\"$NAS_MOUNT_POINT\"" >> "$INSTALL_DIR/.env"
    fi
    
    if [ ! -z "$NAS_IP" ]; then
        echo "NEURALSYNC_NAS_IP=\"$NAS_IP\"" >> "$INSTALL_DIR/.env"
        echo "NEURALSYNC_NAS_USERNAME=\"$NAS_USERNAME\"" >> "$INSTALL_DIR/.env"
        echo "NEURALSYNC_NAS_PASSWORD=\"$NAS_PASSWORD\"" >> "$INSTALL_DIR/.env"
    fi
    
    # Ask for AI API keys
    echo ""
    echo -e "${BLUE}🔑 AI Provider API Keys${NC}"
    echo "Configure API keys for AI providers (optional but recommended):"
    echo ""
    
    read -p "Enter OpenAI API Key (optional, press Enter to skip): " openai_key
    if [ ! -z "$openai_key" ]; then
        sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" "$INSTALL_DIR/.env"
    fi
    
    read -p "Enter Anthropic API Key (optional, press Enter to skip): " anthropic_key
    if [ ! -z "$anthropic_key" ]; then
        echo "ANTHROPIC_API_KEY=$anthropic_key" >> "$INSTALL_DIR/.env"
    fi
    
    read -p "Enter Google AI API Key (optional, press Enter to skip): " google_key
    if [ ! -z "$google_key" ]; then
        echo "GOOGLE_AI_API_KEY=$google_key" >> "$INSTALL_DIR/.env"
    fi
    
    success "Environment configured with personalized settings"
}

# Final setup with auto-start capability
final_setup_with_autostart() {
    log "Performing final setup..."
    
    cd "$INSTALL_DIR"
    
    # Pull Docker images
    log "Pulling Docker images..."
    source "$VENV_DIR/bin/activate"
    docker-compose pull
    
    # Ask user if they want to auto-start everything
    echo ""
    echo -e "${BLUE}🚀 Auto-Start Configuration${NC}"
    echo "Would you like to automatically start NeuralSync and launch AI agents?"
    echo "This will:"
    echo "  • Start all NeuralSync services (Docker containers)"
    echo "  • Launch detected AI agents in the background"
    echo "  • Verify everything is working"
    echo ""
    read -p "Auto-start NeuralSync now? (Y/n): " auto_start
    
    if [[ ! $auto_start =~ ^[Nn]$ ]]; then
        log "Auto-starting NeuralSync with all detected AI agents..."
        
        # Use the neuralsync command for auto-start
        "$INSTALL_DIR/bin/neuralsync" autostart
        
        success "NeuralSync auto-started successfully!"
        
        echo ""
        echo -e "${GREEN}🎯 Quick Commands:${NC}"
        echo -e "  ${BLUE}neuralsync status${NC}      - Check system status"
        echo -e "  ${BLUE}neuralsync ai claude${NC}   - Launch Claude Code"
        echo -e "  ${BLUE}neuralsync ai list${NC}     - Show available AIs"
        echo -e "  ${BLUE}neuralsync health${NC}      - Full system health check"
        
    else
        log "Skipping auto-start. You can start manually with: neuralsync autostart"
        
        # Just test that we can pull images and basic setup works
        log "Testing basic setup..."
        docker-compose up -d --no-deps postgres qdrant neo4j
        sleep 10
        docker-compose down
        
        success "Basic setup verified!"
    fi
    
    success "NeuralSync installation complete!"
}

# Main installation flow
main() {
    log "Starting NeuralSync installation..."
    
    detect_os
    detect_package_managers
    get_user_preferences
    install_system_dependencies
    detect_ai_clis
    install_missing_ai_clis
    scan_ai_configurations
    create_directory_structure
    create_python_venv
    compile_base_memory
    configure_unrestricted_mode
    clone_and_setup_neuralsync
    setup_path
    configure_environment
    final_setup_with_autostart
    
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