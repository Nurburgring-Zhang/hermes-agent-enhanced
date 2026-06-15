#!/bin/bash
# ============================================================================
# Hermes - One-Click Installer
# Cross-platform: Linux / macOS / WSL2 / Termux
# ============================================================================
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${HERMES_HOME}/backups/pre-enhanced-$(date +%Y%m%d_%H%M%S)"

banner() {
    echo -e "${BLUE}"
    echo "  ╔══════════════════════════════════════════════════╗"
    echo "  ║     Hermes v1.0 Installer                       ║"
    echo "  ║     150+ Enhancement Modules for Hermes Agent    ║"
    echo "  ║     By Community | For Community                 ║"
    echo "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }

check_prerequisites() {
    echo "=== Checking Prerequisites ==="
    
    # Check if hermes is installed
    if ! command -v hermes &>/dev/null && [ ! -f "$HERMES_HOME/hermes-agent/venv/bin/python" ]; then
        err "Hermes Agent not found!"
        echo "  Install official Hermes first:"
        echo "  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
        echo ""
        read -p "Install official Hermes now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
            log "Hermes installed"
        else
            err "Please install Hermes first, then re-run this installer."
            exit 1
        fi
    else
        log "Hermes Agent found"
    fi
    
    # Check Python
    if ! command -v python3 &>/dev/null; then
        err "Python3 not found. Please install Python 3.11+"
        exit 1
    fi
    log "Python3 found: $(python3 --version)"
    
    # Check HERMES_HOME exists
    if [ ! -d "$HERMES_HOME" ]; then
        warn "HERMES_HOME ($HERMES_HOME) not found, creating..."
        mkdir -p "$HERMES_HOME"
    fi
    log "HERMES_HOME: $HERMES_HOME"
}

backup_existing() {
    echo ""
    echo "=== Backing Up Existing Configuration ==="
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup existing SOUL.md, AGENTS.md, config
    [ -f "$HERMES_HOME/SOUL.md" ] && cp "$HERMES_HOME/SOUL.md" "$BACKUP_DIR/" && log "Backed up SOUL.md"
    [ -f "$HERMES_HOME/AGENTS.md" ] && cp "$HERMES_HOME/AGENTS.md" "$BACKUP_DIR/" && log "Backed up AGENTS.md"
    [ -f "$HERMES_HOME/config.yaml" ] && cp "$HERMES_HOME/config.yaml" "$BACKUP_DIR/" && log "Backed up config.yaml"
    
    # Backup existing scripts (if any)
    [ -d "$HERMES_HOME/scripts" ] && cp -r "$HERMES_HOME/scripts" "$BACKUP_DIR/scripts_backup" && log "Backed up scripts/"
    
    log "Backup saved to: $BACKUP_DIR"
}

install_core() {
    echo ""
    echo "=== Installing Core Enhancement Modules ==="
    
    # Scripts directory
    if [ -d "$SCRIPT_DIR/core/scripts" ]; then
        mkdir -p "$HERMES_HOME/scripts"
        cp -r "$SCRIPT_DIR/core/scripts/"* "$HERMES_HOME/scripts/" 2>/dev/null
        local count=$(find "$HERMES_HOME/scripts" -name '*.py' -o -name '*.sh' | wc -l)
        log "Installed $count scripts to ~/.hermes/scripts/"
    fi
    
    # Agent directory (three-layer cognitive architecture)
    if [ -d "$SCRIPT_DIR/core/agent" ]; then
        mkdir -p "$HERMES_HOME/agent"
        cp -r "$SCRIPT_DIR/core/agent/"* "$HERMES_HOME/agent/" 2>/dev/null
        log "Installed agent modules (monitor/reflector/model_router)"
    fi
    
    # Tools directory
    if [ -d "$SCRIPT_DIR/core/tools" ]; then
        mkdir -p "$HERMES_HOME/tools"
        cp -r "$SCRIPT_DIR/core/tools/"* "$HERMES_HOME/tools/" 2>/dev/null
        log "Installed tools (progress_tool)"
    fi
    
    # Production loop
    if [ -d "$SCRIPT_DIR/core/production_loop" ]; then
        mkdir -p "$HERMES_HOME/production_loop"
        cp -r "$SCRIPT_DIR/core/production_loop/"* "$HERMES_HOME/production_loop/" 2>/dev/null
        log "Installed production loop engine (8 modules)"
    fi
    
    # Auto engine (self-evolution)
    if [ -d "$SCRIPT_DIR/core/auto_engine" ]; then
        mkdir -p "$HERMES_HOME/auto_engine"
        cp -r "$SCRIPT_DIR/core/auto_engine/"* "$HERMES_HOME/auto_engine/" 2>/dev/null
        log "Installed auto engine (self-evolution + multi-agent orchestrator)"
    fi
    
    # Evolution v3
    if [ -d "$SCRIPT_DIR/core/evolution_v3" ]; then
        mkdir -p "$HERMES_HOME/evolution_v3"
        cp -r "$SCRIPT_DIR/core/evolution_v3/"* "$HERMES_HOME/evolution_v3/" 2>/dev/null
        log "Installed evolution_v3 (18 modules: 7-channel memory, GEPA, hooks, subagent mgr)"
    fi
    
    # Core root files
    for f in run_agent.py actor_base.py start_all.py memory_federation.py topology_engine.py synapse_bus.py unified_dashboard.py world_monitor_web.py production_pipeline.py; do
        [ -f "$SCRIPT_DIR/core/$f" ] && cp "$SCRIPT_DIR/core/$f" "$HERMES_HOME/" && log "Installed $f"
    done
}

install_skills() {
    echo ""
    echo "=== Installing Skills ==="
    
    if [ -d "$SCRIPT_DIR/skills" ]; then
        mkdir -p "$HERMES_HOME/skills"
        cp -r "$SCRIPT_DIR/skills/"* "$HERMES_HOME/skills/" 2>/dev/null
        local count=$(find "$HERMES_HOME/skills" -maxdepth 1 -type d | wc -l)
        log "Installed $((count-1)) skill directories"
    fi
}

install_plugins() {
    echo ""
    echo "=== Installing Plugins ==="
    
    if [ -d "$SCRIPT_DIR/plugins" ]; then
        mkdir -p "$HERMES_HOME/plugins"
        cp -r "$SCRIPT_DIR/plugins/"* "$HERMES_HOME/plugins/" 2>/dev/null
        log "Installed plugins"
    fi
    
    # Extras (hermes-plugin-lineworks, docker config)
    if [ -d "$SCRIPT_DIR/extras" ]; then
        local extras_dir="$HERMES_HOME/extras"
        mkdir -p "$extras_dir"
        cp -r "$SCRIPT_DIR/extras/"* "$extras_dir/" 2>/dev/null
        log "Installed extras (lineworks plugin, docker config)"
    fi
}

install_config() {
    echo ""
    echo "=== Installing Configuration ==="
    
    # SOUL.md (the core enhancement rules)
    if [ -f "$SCRIPT_DIR/config/SOUL.md" ]; then
        cp "$SCRIPT_DIR/config/SOUL.md" "$HERMES_HOME/SOUL.md"
        log "Installed SOUL.md (enhanced agent personality + rules)"
    fi
    
    # AGENTS.md
    if [ -f "$SCRIPT_DIR/config/AGENTS.md" ]; then
        cp "$SCRIPT_DIR/config/AGENTS.md" "$HERMES_HOME/AGENTS.md"
        log "Installed AGENTS.md (enhanced execution rules)"
    fi
    
    # Config template (don't overwrite existing)
    if [ -f "$SCRIPT_DIR/config/config.yaml" ]; then
        if [ ! -f "$HERMES_HOME/config.yaml" ]; then
            cp "$SCRIPT_DIR/config/config.yaml" "$HERMES_HOME/config.yaml"
            log "Installed config.yaml (template - please configure API keys)"
        else
            cp "$SCRIPT_DIR/config/config.yaml" "$HERMES_HOME/config.yaml.enhanced-template"
            warn "config.yaml exists, saved as config.yaml.enhanced-template"
        fi
    fi
    
    # .env template
    cat > "$HERMES_HOME/.env.template" << 'ENVEOF'
# Hermes Enhanced Pack - Environment Variables
# Copy to .env and fill in your values

# LLM Provider API Keys
DEEPSEEK_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Messaging Tokens (optional)
TELEGRAM_BOT_TOKEN=your_token_here
DISCORD_BOT_TOKEN=your_token_here

# Pushplus Token (optional)
PUSHPLUS_TOKEN=your_token_here

# Local LLM (optional, for Hy-Memory LLM features)
LM_STUDIO_URL=http://localhost:1234/v1
OLLAMA_URL=http://localhost:11434

HERMES_HOME=~/.hermes
ENVEOF
    log "Created .env.template"
}

install_services() {
    echo ""
    echo "=== Installing Systemd Services ==="
    
    # Only install on Linux/WSL with systemd
    if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
        # Install hermes-gateway service
        if [ -f "$SCRIPT_DIR/services/hermes-gateway.service" ]; then
            local svc_file="$SCRIPT_DIR/services/hermes-gateway.service"
            # Update paths for current user
            sed "s|User=.*|User=$(whoami)|g; s|Group=.*|Group=$(whoami)|g; s|/home/[^/]*/\.hermes|$HERMES_HOME|g" \
                "$svc_file" > /tmp/hermes-gateway.service 2>/dev/null
            warn "Service file prepared at /tmp/hermes-gateway.service"
            warn "Install manually: sudo cp /tmp/hermes-gateway.service /etc/systemd/system/ && sudo systemctl enable hermes-gateway"
        fi
        
        # Install user services
        mkdir -p "$HOME/.config/systemd/user"
        if [ -f "$SCRIPT_DIR/services/hermes-eternal.service" ]; then
            sed "s|/home/[^/]*/\.hermes|$HERMES_HOME|g; s|User=.*||g" \
                "$SCRIPT_DIR/services/hermes-eternal.service" > "$HOME/.config/systemd/user/hermes-eternal.service" 2>/dev/null
            log "Installed hermes-eternal user service"
        fi
    else
        warn "systemd not available - service files saved to $SCRIPT_DIR/services/"
        warn "On macOS/Termux, use launchd or manual process management"
    fi
}

install_crontab() {
    echo ""
    echo "=== Installing Cron Jobs ==="
    
    if ! command -v crontab &>/dev/null; then
        warn "crontab not available, skipping cron installation"
        return
    fi
    
    if [ -f "$SCRIPT_DIR/config/crontab_backup.txt" ]; then
        # Update paths in crontab
        sed "s|/home/[^/]*/\.hermes|$HERMES_HOME|g" "$SCRIPT_DIR/config/crontab_backup.txt" > /tmp/hermes_crontab.txt 2>/dev/null
        
        read -p "Install cron jobs? This will ADD to your existing crontab. (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Append (not replace) to existing crontab
            (crontab -l 2>/dev/null; echo "# === Hermes Enhanced Pack ==="; cat /tmp/hermes_crontab.txt) | crontab -
            log "Cron jobs installed ($(wc -l < /tmp/hermes_crontab.txt) entries)"
        else
            warn "Cron jobs saved to /tmp/hermes_crontab.txt - install manually with: crontab /tmp/hermes_crontab.txt"
        fi
    fi
}

install_dependencies() {
    echo ""
    echo "=== Installing Python Dependencies ==="
    
    # Install common dependencies
    local deps="playwright requests beautifulsoup4 lxml feedparser jieba numpy scipy scikit-learn sentence-transformers aiohttp flask fastapi uvicorn sqlalchemy aiosqlite apscheduler"
    
    if command -v pip3 &>/dev/null; then
        warn "Installing Python dependencies (this may take a few minutes)..."
        pip3 install --quiet $deps 2>/dev/null || warn "Some dependencies may need manual installation"
        log "Python dependencies installed"
    elif command -v pip &>/dev/null; then
        pip install --quiet $deps 2>/dev/null || warn "Some dependencies may need manual installation"
        log "Python dependencies installed"
    else
        warn "pip not found, please install dependencies manually"
    fi
    
    # Install playwright browsers if playwright was installed
    if python3 -c "import playwright" 2>/dev/null; then
        warn "Installing Playwright browsers..."
        python3 -m playwright install chromium 2>/dev/null || warn "Playwright browser install failed (optional)"
    fi
}

post_install() {
    echo ""
    echo "=== Post-Installation ==="
    
    # Create necessary directories
    mkdir -p "$HERMES_HOME/logs"
    mkdir -p "$HERMES_HOME/reports"
    mkdir -p "$HERMES_HOME/reports/context_sections"
    mkdir -p "$HERMES_HOME/state"
    mkdir -p "$HERMES_HOME/refs"
    mkdir -p "$HERMES_HOME/workspace"
    mkdir -p "$HERMES_HOME/checkpoints"
    log "Created required directories"
    
    # Make scripts executable
    find "$HERMES_HOME/scripts" -name '*.sh' -exec chmod +x {} \; 2>/dev/null
    find "$HERMES_HOME/scripts" -name '*.py' -exec chmod +x {} \; 2>/dev/null
    log "Scripts made executable"
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Installation Complete!                              ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}║  Next steps:                                         ║${NC}"
    echo -e "${GREEN}║  1. Configure API keys:                              ║${NC}"
    echo -e "${GREEN}║     cp ~/.hermes/.env.template ~/.hermes/.env        ║${NC}"
    echo -e "${GREEN}║     nano ~/.hermes/.env                              ║${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}║  2. Update config.yaml with your model provider:     ║${NC}"
    echo -e "${GREEN}║     nano ~/.hermes/config.yaml                       ║${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}║  3. Start Hermes:                                    ║${NC}"
    echo -e "${GREEN}║     hermes                                           ║${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}║  4. Enable services (optional):                      ║${NC}"
    echo -e "${GREEN}║     systemctl --user enable hermes-eternal           ║${NC}"
    echo -e "${GREEN}║     systemctl --user start hermes-eternal            ║${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
}

# Main installation flow
banner
check_prerequisites
backup_existing
install_core
install_skills
install_plugins
install_config
install_services
install_crontab
install_dependencies
post_install
