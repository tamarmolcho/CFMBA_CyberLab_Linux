#!/bin/bash
# Import Virtual Machine
read -p "Please provide OVA file name: " vmname
if [ -f "$vmname" ]; then
    vboxmanage import "$vmname"
else
    echo "[!] Error: File '$vmname' not found."
    exit 1
fi
