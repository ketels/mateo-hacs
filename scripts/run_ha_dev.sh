#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
VENV_DIR="${PROJECT_ROOT}/.ha-venv"
CONFIG_DIR="${PROJECT_ROOT}/dev_config"
LOG_FILE="${CONFIG_DIR}/home-assistant.dev.log"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[run] Missing venv. Run scripts/reset_ha_dev.sh first" >&2
  exit 1
fi
source "$VENV_DIR/bin/activate"

# Kill existing
pkill -f "hass --config ${CONFIG_DIR}" 2>/dev/null || true

# Start
nohup hass --config "$CONFIG_DIR" --debug > "$LOG_FILE" 2>&1 &
PID=$!
echo "[run] Started Home Assistant (pid=${PID}) logging to $LOG_FILE"
echo "[run] Tail logs: tail -f $LOG_FILE"
echo "[run] Open UI: http://localhost:8123/"
