#!/bin/bash
# Start Virtual Machine
echo "=== Start Virtual Machine ==="
vboxmanage list vms
read -p "Enter VM Name or UUID to start: " vmname
if [ -n "$vmname" ]; then
    vboxmanage startvm "$vmname" --type headless
fi
