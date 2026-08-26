#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f /proc/device-tree/model ]] || ! grep -qi raspberry /proc/device-tree/model; then
  echo "Run this setup on the Raspberry Pi."
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  echo "Do not run setup-pi.sh as root. Use your desktop user, e.g. cyberdeck-pi."
  exit 1
fi

echo "Installing system packages (sudo)..."
sudo apt-get update
sudo apt-get install -y \
  python3-venv \
  python3-pip \
  python3-dev \
  libsdl2-2.0-0 \
  libsdl2-image-2.0-0 \
  libsdl2-mixer-2.0-0 \
  libsdl2-ttf-2.0-0 \
  libfreetype6 \
  fonts-liberation \
  fonts-dejavu-core

if [[ -d "${PROJECT_DIR}/.venv" && ! -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  rm -rf "${PROJECT_DIR}/.venv"
fi

if [[ ! -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  python3 -m venv "${PROJECT_DIR}/.venv"
fi

"${PROJECT_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${PROJECT_DIR}/.venv/bin/python" -m pip install -r "${PROJECT_DIR}/requirements-pi.txt"

echo
echo "Setup complete. Install the desktop icon with:"
echo "  ${PROJECT_DIR}/pi/install-desktop-launcher.sh"
echo "Then double-click Keystroke Spike on the desktop."
