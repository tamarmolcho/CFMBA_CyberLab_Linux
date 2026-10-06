#!/bin/bash
# Check VM Network Connectivity
echo "=== Check VM Network Connectivity ==="
vmslist=( $(vboxmanage list vms) )
vmarr=()
for liner in "${vmslist[@]}"; do
    if [[ $liner = {* ]]; then
        vmarr+=(${liner})
    fi
done

if [ ${#vmarr[@]} -eq 0 ]; then
    echo "[!] No Virtual Machines found."
    exit 0
fi

echo "Available VMs List:"
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
echo "[*] Querying IP from: $chosen_vm"
vboxmanage guestproperty get "$chosen_vm" "/VirtualBox/GuestInfo/Net/0/V4/IP"
