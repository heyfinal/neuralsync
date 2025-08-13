# NeuralSync Installation Guide

```
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
```

## 🚀 One-Click Installation

The fastest way to get NeuralSync running on any system:

```bash
curl -fsSL https://raw.githubusercontent.com/heyfinal/neuralsync/main/install.sh | bash
```

Or download and run manually:

```bash
wget https://raw.githubusercontent.com/heyfinal/neuralsync/main/install.sh
chmod +x install.sh
./install.sh
```

## 🎯 What the Installer Does

### **Interactive Setup & Personalization**
- 👋 **Personal Configuration**: Asks for your name for AI personalization
- 🔐 **Admin Account**: Creates username/password for NeuralSync management
- 💾 **NAS Integration**: Configures network storage (mount point or IP/credentials)
- 🔍 **AI Config Discovery**: Scans for existing AI configs (.claude.md, .cursor-rules, etc.)
- 📚 **Base Memory**: Compiles found configs into prime directive system

### **Auto-Detection & Smart Installation**
- ✅ Detects your operating system (macOS, Linux)
- ✅ Identifies available AI CLIs (Claude Code, CodexCLI, Autopilot, Aider, Gemini)
- ✅ Installs missing dependencies without breaking system packages
- ✅ Creates isolated Python virtual environment
- ✅ Configures Docker and required services

### **AI CLI Configuration**
- ✅ **Claude Code**: Unrestricted file access, network, system commands
- ✅ **CodexCLI**: Auto-execution, unrestricted mode
- ✅ **Autopilot CLI**: Permissionless GitHub Copilot integration
- ✅ **Aider CLI**: Auto-commits, no safety restrictions
- ✅ **Google AI CLI**: Unrestricted Gemini integration

### **Directory Structure Created**
```
~/.neuralsync/
├── bin/                    # Executable scripts
│   ├── neuralsync         # Master control script
│   ├── claude-unrestricted
│   ├── codex-unrestricted
│   ├── autopilot-unrestricted
│   ├── aider-unrestricted
│   └── gemini-unrestricted
├── config/                # Configuration files
│   ├── base_memory.md     # Compiled AI configurations
│   └── prime_directive.md # AI behavior directives
├── data/                  # Persistent data storage
├── services/              # API and worker services
├── bus/                   # AI communication bus
├── venv/                  # Python virtual environment
└── .env                   # Environment configuration
```

## 🔧 Post-Installation Usage

After installation, restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc
```

### **Master Control Commands**
```bash
neuralsync start           # Start all services
neuralsync stop            # Stop all services  
neuralsync status          # Check service status
neuralsync logs            # View service logs
neuralsync config          # Edit configuration
```

### **AI CLI Integration**
```bash
neuralsync ai claude       # Launch Claude Code (unrestricted)
neuralsync ai codex        # Launch CodexCLI (unrestricted) 
neuralsync ai autopilot    # Launch Autopilot (unrestricted)
neuralsync ai aider        # Launch Aider (unrestricted)
neuralsync ai gemini       # Launch Google AI (unrestricted)
```

## 🛡️ Unrestricted Mode Features

Each AI CLI is configured for maximum autonomy:

### **Claude Code Unrestricted**
- File system access: Full read/write permissions
- Network access: Unrestricted web requests
- System commands: Can execute system operations
- Package installs: Can install dependencies
- Docker access: Full container management

### **CodexCLI Unrestricted**  
- Auto-execution: Runs code without confirmation
- File operations: Unrestricted file access
- Network requests: Can make API calls freely

### **Autopilot Unrestricted**
- GitHub integration: Full repository access
- Code generation: Unrestricted code suggestions
- Auto-commits: Can commit changes directly

### **Aider Unrestricted**
- Auto-commits: Automatically commits changes
- No safety prompts: Skips confirmation dialogs
- Full file access: Can modify any project file

### **Gemini Unrestricted**
- Google AI integration: Full API access
- Auto-execution: Runs generated code
- Network operations: Unrestricted web access

## 🔐 Security Considerations

**⚠️ Important**: Unrestricted mode removes safety guardrails. Only use:
- On trusted systems
- For development/testing environments  
- When you understand the implications

For production use, modify the configuration files in `~/.neuralsync/config/` to add appropriate restrictions.

## 🐛 Troubleshooting

### **Docker Issues**
```bash
# On macOS: Ensure Docker Desktop is running
open /Applications/Docker.app

# On Linux: Start Docker service
sudo systemctl start docker
```

### **Permission Issues**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

### **API Key Configuration**
```bash
# Edit environment variables
neuralsync config

# Or manually edit
nano ~/.neuralsync/.env
```

### **Service Status Check**
```bash
neuralsync status
neuralsync logs
curl http://localhost:8080/health
```

## 📋 System Requirements

### **Minimum Requirements**
- 4GB RAM
- 2GB disk space
- Docker support
- Internet connection

### **Supported Systems**
- macOS 10.15+ (Catalina and newer)
- Ubuntu 18.04+ / Debian 10+
- CentOS 7+ / RHEL 7+
- Other Docker-compatible Linux distributions

### **Supported AI CLIs**
- Claude Code (Anthropic)
- CodexCLI (OpenAI)
- GitHub Copilot CLI / Autopilot
- Aider (AI pair programming)
- Google AI CLI (Gemini)

## 🎮 Quick Start Example

```bash
# Install NeuralSync
curl -fsSL https://raw.githubusercontent.com/heyfinal/neuralsync/main/install.sh | bash

# Restart terminal
source ~/.bashrc

# Check installation
neuralsync status

# Launch Claude Code in unrestricted mode
neuralsync ai claude

# Start a new project with AI assistance
mkdir my-project && cd my-project
neuralsync ai aider "Create a Python web API with FastAPI"
```

Happy AI orchestration! 🤖