#!/bin/bash
# ─────────────────────────────────────────────────
# Story Workflow — Streamlit Dashboard Launcher
# ─────────────────────────────────────────────────
# Key design: this script always exits quickly so the .app
# stops bouncing in the Dock. Streamlit and the watchdog
# run as fully detached background processes.

SCRIPT_DIR="/Users/Gong/workspace/writer-utilities/workflows/short-story-workflow"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="/usr/local/bin/python3.12"
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_STREAMLIT="$VENV_DIR/bin/streamlit"
VENV_PIP="$VENV_DIR/bin/pip"
DASHBOARD="$SCRIPT_DIR/dashboard.py"
LOG="$SCRIPT_DIR/.dashboard.log"
PIDFILE="$SCRIPT_DIR/.streamlit.pid"
PORT=8501

# ── Ensure basic tools are on PATH (macOS .app has minimal PATH) ──
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# ── Helper: focus or open the Streamlit tab in Chrome ──
focus_chrome_tab() {
    osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    activate
    set found to false
    if (count of windows) > 0 then
        repeat with w in windows
            set tabIndex to 0
            repeat with t in tabs of w
                set tabIndex to tabIndex + 1
                if URL of t contains "localhost:8501" then
                    set active tab index of w to tabIndex
                    set index of w to 1
                    set found to true
                    exit repeat
                end if
            end repeat
            if found then exit repeat
        end repeat
    end if
    if not found then
        if (count of windows) is 0 then
            make new window with properties {mode:"normal"}
        end if
        tell window 1 to make new tab with properties {URL:"http://localhost:8501"}
    end if
end tell
APPLESCRIPT
}

# ── If Streamlit is already running, focus and exit immediately ──
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        focus_chrome_tab
        exit 0
    else
        rm -f "$PIDFILE"
    fi
fi

# Also check if something is already listening on the port
if curl -s -o /dev/null http://localhost:$PORT 2>/dev/null; then
    focus_chrome_tab
    exit 0
fi

# ── Kill anything stale on the port ──
lsof -ti:$PORT | xargs kill 2>/dev/null || true

# ── First-run setup ──
if [ ! -f "$VENV_STREAMLIT" ]; then
    osascript -e 'display notification "Setting up Story Workflow for the first time..." with title "Story Workflow"'

    "$PYTHON" -m venv "$VENV_DIR" 2>>"$LOG"
    "$VENV_PIP" install --upgrade pip >>"$LOG" 2>&1
    "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" >>"$LOG" 2>&1

    if command -v npm &>/dev/null; then
        npm install -g docx >>"$LOG" 2>&1 || true
    fi

    osascript -e 'display notification "Setup complete! Launching dashboard..." with title "Story Workflow"'
fi

# ── Launch everything in a detached subshell ──
# The .app process exits immediately; Streamlit lives on its own.
nohup bash -c '
    SCRIPT_DIR="'"$SCRIPT_DIR"'"
    VENV_STREAMLIT="'"$VENV_STREAMLIT"'"
    DASHBOARD="'"$DASHBOARD"'"
    LOG="'"$LOG"'"
    PIDFILE="'"$PIDFILE"'"
    PORT='"$PORT"'

    cd "$SCRIPT_DIR"

    "$VENV_STREAMLIT" run "$DASHBOARD" \
        --server.headless true \
        --browser.gatherUsageStats false \
        --server.port $PORT \
        >>"$LOG" 2>&1 &

    STREAMLIT_PID=$!
    echo "$STREAMLIT_PID" > "$PIDFILE"

    # Wait for server to be ready
    for i in 1 2 3 4 5 6 7 8 9 10; do
        sleep 1
        if curl -s -o /dev/null http://localhost:$PORT 2>/dev/null; then
            break
        fi
    done

    # Open Chrome tab
    osascript -e "tell application \"Google Chrome\" to activate" \
              -e "tell application \"Google Chrome\" to tell window 1 to make new tab with properties {URL:\"http://localhost:'"$PORT"'\"}"

    # Watchdog: kill Streamlit when browser disconnects
    sleep 10
    IDLE_COUNT=0
    while true; do
        if ! kill -0 "$STREAMLIT_PID" 2>/dev/null; then
            break
        fi
        CONNS=$(lsof -i:$PORT -sTCP:ESTABLISHED 2>/dev/null | grep -c ESTABLISHED || true)
        if [ "$CONNS" -eq 0 ]; then
            IDLE_COUNT=$((IDLE_COUNT + 1))
            if [ "$IDLE_COUNT" -ge 3 ]; then
                kill "$STREAMLIT_PID" 2>/dev/null
                rm -f "$PIDFILE"
                exit 0
            fi
        else
            IDLE_COUNT=0
        fi
        sleep 5
    done
    rm -f "$PIDFILE"
' >>"$LOG" 2>&1 &

# Give it just a moment so the PID file gets written
sleep 1
exit 0
