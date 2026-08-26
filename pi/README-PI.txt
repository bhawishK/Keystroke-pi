Keystroke Spike — Raspberry Pi bundle
=====================================

Extract this archive to your home directory:

  tar -xzf keystroke-spike-pi-*.tar.gz -C ~

You should have:

  ~/keystroke-spike/

First-time setup
----------------
1. Install Python packages (once, needs sudo for apt):

     cd ~/keystroke-spike
     ./scripts/setup-pi.sh

2. Install the desktop icon (no sudo):

     ./pi/install-desktop-launcher.sh

3. Double-click **Keystroke Spike** on the desktop.

   The first click may ask you to trust the launcher — choose Execute /
   Allow Launching. The app opens fullscreen on the 720 × 720 display.

Close the app
-------------
Press Esc.

Hold Backspace for 2 seconds to reset the learned model and clear all lines.

Manual run (no desktop icon)
----------------------------
  cd ~/keystroke-spike
  ./scripts/run-pi.sh

Windowed instead of fullscreen:

  ./scripts/run-pi.sh --window

Replace install on Pi
---------------------
  rm -rf ~/keystroke-spike
  tar -xzf ~/keystroke-spike-pi-*.tar.gz -C ~
  cd ~/keystroke-spike
  ./scripts/setup-pi.sh
  ./pi/install-desktop-launcher.sh

Rebuild bundle on Mac
---------------------
  cd 01-project/cyberdeck/keystroke-spike-pi
  ./scripts/build-pi-bundle.sh
