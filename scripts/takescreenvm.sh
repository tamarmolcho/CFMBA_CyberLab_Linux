#!/bin/bash
# Capturing VM Screenshot
echo "=== Capturing VM Screenshot ==="
vmslist=( $(vboxmanage list runningvms) )
vmarr=()
for liner in "${vmslist[@]}"; do
    if [[ $liner = {* ]]; then
        vmarr+=(${liner})
    fi
done

if [ ${#vmarr[@]} -eq 0 ]; then
    echo "[!] No running Virtual Machines found to capture screenshot."
    exit 0
fi

echo "Running VMs List:"
let i=1
for vm in "${vmarr[@]}"; do
    echo "($i): $vm"
    let "i=i+1"
done

read -p "Choose VM number (1-${#vmarr[@]}): " vmnum
if [ -z "$vmnum" ] || [ "$vmnum" -lt 1 ] || [ "$vmnum" -gt "${#vmarr[@]}" ]; then
    echo "[!] Invalid VM selection."
    exit 1
fi

chosen_vm="${vmarr[$((vmnum-1))]}"
echo "[*] Grabbing screenshot from: $chosen_vm"
imgname=$(date +"%Y%m%d_%H%M%S")
capturen="screenshot_${imgname}.png"
vboxmanage controlvm "$chosen_vm" screenshotpng "$capturen"
echo "[+] Saved screenshot as: $capturen"
