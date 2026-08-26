#!/usr/bin/env bash
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
LOG_FILE="${PROJECT_DIR}/launch.log"

{
  echo "---- $(date) ----"
  echo "DISPLAY=${DISPLAY:-unset} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}"
} >> "${LOG_FILE}"

show_error() {
  local message="$1"
  echo "${message}" | tee -a "${LOG_FILE}"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --text="${message}" 2>/dev/null || true
  fi
}

if [[ ! -x "${PYTHON_BIN}" ]]; then
  show_error "Keystroke Spike is not set up yet. In Terminal run:
cd ~/keystroke-spike && ./scripts/setup-pi.sh"
  exit 1
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  export DISPLAY=:0
fi

cd "${PROJECT_DIR}"
set +e
if [[ "${1:-}" == "--window" ]]; then
  shift
  "${PYTHON_BIN}" src/main.py --window "$@" >> "${LOG_FILE}" 2>&1
else
  "${PYTHON_BIN}" src/main.py --fullscreen "$@" >> "${LOG_FILE}" 2>&1
fi
status=$?
set -e
if [[ "${status}" -ne 0 ]]; then
  show_error "Keystroke Spike failed to start.
See ${LOG_FILE}"
  exit "${status}"
fi
