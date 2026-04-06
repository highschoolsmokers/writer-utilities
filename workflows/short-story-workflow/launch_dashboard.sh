#!/bin/bash
# ─────────────────────────────────────────────────
# Story Workflow — Streamlit Dashboard Launcher
# ─────────────────────────────────────────────────
# On first run, creates a virtual environment and installs dependencies.
# On subsequent runs, activates the venv and launches the dashboard.
#
# Auto-quit: shuts itself down when you close the browser tab.
# Manual quit: right-click → Quit in the Dock also works.

SCRIPT_DIR="/Users/Gong/workspace/writer-utilities/workflows/short-story-workflow"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="/usr/local/bin/python3.12"
DASHBOARD="$SCRIPT_DIR/dashboard.py"
LOG="$SCRIPT_DIR/.dashboard.log"
PIDFILE="$SCRIPT_DIR/.streamlit.pid"

# ── Kill any leftover Streamlit from a previous run ──
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    kill "$OLD_PID" 2>/dev/null
    rm -f "$PIDFILE"
fi
lsof -ti:8501 | xargs kill 2>/dev/null || true

# ── Cleanup function — runs on Quit / shutdown / tab close ──
cleanup() {
    kill "$WATCHDOG_PID" 2>/dev/null
    kill "$STREAMLIT_PID" 2>/dev/null
    wait "$STREAMLIT_PID" 2>/dev/null
    rm -f "$PIDFILE"
    exit 0
}
trap cleanup SIGTERM SIGINT SIGHUP EXIT

# ── First-run setup ──
if [ ! -d "$VENV_DIR" ]; then
    osascript -e 'display notification "Setting up Story Workflow for the first time..." with title "Story Workflow"'

    "$PYTHON" -m venv "$VENV_DIR" 2>>"$LOG"

    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip >>"$LOG" 2>&1
    pip install -r "$SCRIPT_DIR/requirements.txt" >>"$LOG" 2>&1

    if command -v npm &>/dev/null; then
        npm install -g docx >>"$LOG" 2>&1 || true
    fi

    osascript -e 'display notification "Setup complete! Launching dashboard..." with title "Story Workflow"'
else
    source "$VENV_DIR/bin/activate"
fi

# ── Launch Streamlit ──
cd "$SCRIPT_DIR"

streamlit run "$DASHBOARD" \
    --server.headless true \
    --browser.gatherUsageStats false \
    --server.port 8501 \
    2>>"$LOG" &

STREAMLIT_PID=$!
echo "$STREAMLIT_PID" > "$PIDFILE"

# Open browser after Streamlit starts
sleep 2
open http://localhost:8501

# ── Watchdog: auto-quit when browser tab closes ──
# Streamlit keeps a WebSocket connection open while the tab is active.
# When the tab closes, the connection count on port 8501 drops to
# only LISTEN (no ESTABLISHED). We watch for that and shut down.
(
    # Give the browser time to connect before we start checking
    sleep 8

    IDLE_COUNT=0
    while true; do
        # Count ESTABLISHED connections to the Streamlit port
        CONNS=$(lsof -i:8501 -sTCP:ESTABLISHED 2>/dev/null | grep -c ESTABLISHED)

        if [ "$CONNS" -eq 0 ]; then
            IDLE_COUNT=$((IDLE_COUNT + 1))
            # 3 consecutive checks with no connections = tab is closed
            # (15 seconds grace period to handle brief reconnects/refreshes)
            if [ "$IDLE_COUNT" -ge 3 ]; then
                kill "$STREAMLIT_PID" 2>/dev/null
                exit 0
            fi
        else
            IDLE_COUNT=0
        fi

        sleep 5
    done
) &
WATCHDOG_PID=$!

# Wait for Streamlit to exit (via watchdog, Dock quit, or otherwise)
wait "$STREAMLIT_PID"
rm -f "$PIDFILE"
