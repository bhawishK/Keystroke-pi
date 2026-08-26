#!/usr/bin/env bash
# Run on the Pi after extracting the bundle:
#   ~/keystroke-spike/pi/install-desktop-launcher.sh

set -euo pipefail

SPIKE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="${HOME}"
DESKTOP_DIR="${HOME_DIR}/Desktop"
APPS_DIR="${HOME_DIR}/.local/share/applications"
ICON_PATH="${SPIKE_DIR}/pi/keystroke-spike.png"
RUNNER="${SPIKE_DIR}/scripts/run-pi.sh"

if [[ ! -x "${RUNNER}" ]]; then
  echo "Missing launcher script: ${RUNNER}" >&2
  exit 1
fi

mkdir -p "${DESKTOP_DIR}" "${APPS_DIR}"

write_desktop_file() {
  local path="$1"
  cat > "${path}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Keystroke Spike
Comment=Ten-line typing learner
Exec=${RUNNER}
Path=${SPIKE_DIR}
Icon=${ICON_PATH}
Terminal=false
Categories=Utility;
StartupNotify=true
EOF
  chmod +x "${path}"
}

write_desktop_file "${DESKTOP_DIR}/keystroke-spike.desktop"
write_desktop_file "${APPS_DIR}/keystroke-spike.desktop"

if command -v gio >/dev/null 2>&1; then
  gio set "${DESKTOP_DIR}/keystroke-spike.desktop" metadata::trusted true 2>/dev/null || true
fi

echo "Installed desktop launcher:"
echo "  ${DESKTOP_DIR}/keystroke-spike.desktop"
echo ""
echo "If the first click asks whether to execute it, choose Execute / Allow Launching."
echo "Close with Esc. Hold Backspace 2s to reset the model."
