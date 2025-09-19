#!/usr/bin/env bash
set -euo pipefail

# Reset Home Assistant dev environment in isolated .ha-venv
# Safe to re-run; will recreate virtual env and install matching HA + extras.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Auto-detect a suitable Python if PYTHON_BIN not provided.
if [[ -z "${PYTHON_BIN:-}" ]]; then
  for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${PROJECT_ROOT}/.ha-venv"
CONFIG_DIR="${PROJECT_ROOT}/dev_config"

echo "[reset] Using python: $(command -v $PYTHON_BIN || echo not-found)"

if [[ -d "$VENV_DIR" ]]; then
  echo "[reset] Removing existing venv $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

$PYTHON_BIN -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools

# Pin to a known stable version (update as needed). Allow override via env HA_VERSION.
HA_VERSION="${HA_VERSION:-2025.9.3}"
REQS=( "homeassistant==${HA_VERSION}" "home-assistant-intents" "hassil" )

# (Previously forced source builds with PIP_NO_BINARY; keep wheels for speed.)

echo "[reset] Installing core packages: ${REQS[*]}"
pip install "${REQS[@]}"

# Developer helper packages used by tests
pip install pytest pytest-asyncio pytest-cov pytest-homeassistant-custom-component respx

# Link custom component into config if not present
mkdir -p "$CONFIG_DIR/custom_components"
if [[ ! -e "$CONFIG_DIR/custom_components/mateo_meals" ]]; then
  ln -s "$PROJECT_ROOT/custom_components/mateo_meals" "$CONFIG_DIR/custom_components/mateo_meals"
fi

# Clean old recorder database
rm -f "$CONFIG_DIR"/home-assistant_v2.db*

cat <<EOF
[reset] Done.
Activate with: source .ha-venv/bin/activate
Run with: scripts/run_ha_dev.sh
EOF
