#!/bin/bash
# ==============================================================================
# CFMBA CyberLab Operations Center - Kali Linux System Dependencies Installer
# Run with: sudo ./setup_kali.sh
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run with sudo: sudo ./setup_kali.sh"
  exit 1
fi

echo "[*] Updating Kali package repositories..."
apt-get update -y

echo "[*] Installing Python3, Virtual Environment tools, and dependencies..."
apt-get install -y python3 python3-venv python3-pip python3-flask python3-psutil python3-pil

echo "[*] Checking for VirtualBox..."
if ! command -v vboxmanage &> /dev/null; then
    echo "[*] VirtualBox not found. Installing VirtualBox (optional, recommended)..."
    apt-get install -y virtualbox || echo "[!] Notice: VirtualBox package not in default repo or restricted. The app will run in Cyber Range Simulation mode automatically."
else
    echo "[+] VirtualBox is already installed: $(vboxmanage --version)"
fi

echo "========================================================================"
echo "[+] Kali setup completed successfully!"
echo "[*] You can now start the application anytime with:"
echo "    ./run.sh"
echo "========================================================================"
