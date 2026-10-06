#!/bin/bash
# Stop Virtual Machine
echo "=== Stop Virtual Machine ==="
vboxmanage list runningvms
read -p "Enter VM Name or UUID to stop: " vmname
if [ -n "$vmname" ]; then
    echo "[*] Attempting ACPI Graceful Shutdown..."
    vboxmanage controlvm "$vmname" acpipowerbutton || (echo "[*] ACPI failed, forcing power off..."; vboxmanage controlvm "$vmname" poweroff)
fi
