#!/bin/bash
# ============================================================================
# Hermes Gateway WSL Start Script
# ============================================================================
# Use this script to start the Hermes gateway in WSL environments where
# systemd user services may not be fully functional or survive WSL restarts.
#
# Usage:
#   ./start_gateway.sh              # Start in foreground
#   ./start_gateway.sh --daemon     # Start as background daemon
#   ./start_gateway.sh --status     # Check if gateway is running
#   ./start_gateway.sh --stop       # Stop running gateway
#
# This script is the WSL-compatible alternative to:
#   hermes gateway start      (systemd user service)
#   systemctl --user start hermes-gateway
# ============================================================================

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PROJECT_ROOT="$HERMES_HOME/hermes-agent"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
PID_FILE="$HERMES_HOME/run/gateway.pid"
LOG_FILE="$HERMES_HOME/logs/gateway.log"

# Ensure directories exist
mkdir -p "$HERMES_HOME/run" "$HERMES_HOME/logs"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    # Also check for any gateway process
    if pgrep -f "hermes_cli.main gateway run" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE" 2>/dev/null || true
    fi
    pgrep -f "hermes_cli.main gateway run" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_status() {
    if is_running; then
        local pid
        pid=$(get_pid | head -1)
        echo "✓ Gateway is running (PID: $pid)"
        return 0
    else
        echo "✗ Gateway is not running"
        return 1
    fi
}

cmd_stop() {
    if ! is_running; then
        echo "Gateway is not running"
        rm -f "$PID_FILE"
        return 0
    fi

    echo "Stopping gateway..."
    local pids
    pids=$(pgrep -f "hermes_cli.main gateway run" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 2
        # Force kill if still running
        pids=$(pgrep -f "hermes_cli.main gateway run" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
    echo "✓ Gateway stopped"
}

cmd_start() {
    if is_running; then
        echo "Gateway is already running (PID: $(get_pid | head -1))"
        return 1
    fi

    echo "Starting Hermes Gateway..."
    echo "  Project root: $PROJECT_ROOT"
    echo "  Python:       $VENV_PYTHON"
    echo "  Log:          $LOG_FILE"

    if [ ! -f "$VENV_PYTHON" ]; then
        echo "ERROR: Python venv not found at $VENV_PYTHON"
        echo "Run 'hermes setup' first to create the virtual environment."
        return 1
    fi

    if [ "${1:-}" = "--daemon" ]; then
        echo "  Mode:         daemon (background)"
        nohup "$VENV_PYTHON" -m hermes_cli.main gateway run --replace --accept-hooks \
            >> "$LOG_FILE" 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            echo "✓ Gateway started as daemon (PID: $pid)"
        else
            echo "✗ Gateway failed to start. Check $LOG_FILE"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "  Mode:         foreground (Ctrl+C to stop)"
        echo ""
        exec "$VENV_PYTHON" -m hermes_cli.main gateway run --replace --accept-hooks
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case "${1:-}" in
    --status|status)
        cmd_status
        ;;
    --stop|stop)
        cmd_stop
        ;;
    --daemon|-d)
        shift || true
        cmd_start --daemon
        ;;
    --help|-h)
        echo "Usage: $0 [--daemon|--status|--stop|--help]"
        echo ""
        echo "  (no args)    Start gateway in foreground"
        echo "  --daemon     Start gateway as background daemon"
        echo "  --status     Check if gateway is running"
        echo "  --stop       Stop running gateway"
        echo "  --help       Show this help"
        ;;
    *)
        cmd_start
        ;;
esac
