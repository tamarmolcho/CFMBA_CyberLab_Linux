import os
import re
import subprocess
import shutil
import time
import datetime
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Minimal 1x1 transparent/dark PNG fallback if Pillow is not installed
FALLBACK_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\x18\x18\x18\x00\x00\x00\x04\x00\x01\x18\xb9b\x9d\x00\x00\x00\x00IEND\xaeB`\x82'

def find_vbox_binary():
    """Finds the first existing, executable VirtualBox binary across host paths"""
    candidates = [
        shutil.which("vboxmanage"),
        shutil.which("VBoxManage"),
        "/usr/bin/vboxmanage",
        "/usr/bin/VBoxManage",
        "/usr/local/bin/vboxmanage",
        "/usr/local/bin/VBoxManage",
        "/opt/VirtualBox/VBoxManage",
        "/usr/lib/virtualbox/VBoxManage"
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None

VBOX_PATH = find_vbox_binary()

class VBoxManager:
    def __init__(self, static_dir, demo_enabled=True):
        self.vbox_bin = VBOX_PATH
        self.static_dir = static_dir
        self.screenshots_dir = os.path.join(static_dir, "screenshots")
        self.uploads_dir = os.path.join(static_dir, "uploads")
        self.demo_enabled = demo_enabled
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

        # 3-second cache for get_all_vms to optimize high-frequency telemetry polling
        self._vm_cache = None
        self._vm_cache_time = 0
        self._cache_ttl = 3.0

        # In-memory simulated cyber range state (used when demo is active or no host VMs)
        self.simulated_vms = {
            "win7-01": {
                "id": "c77ecb39-8067-4bda-8971-fc27c7a998a3",
                "name": "Win7",
                "os": "Windows 7 (64-bit)",
                "state": "stopped",
                "ip": "192.168.56.101",
                "mac": "08:00:27:C7:7E:CB",
                "cpus": 2,
                "ram": 2048,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Windows Workstation Target",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "win2022_dc_preview.png"
            },
            "kali-2021-02": {
                "id": "14c8915b-61ad-447c-9754-fce69de14ed1",
                "name": "Kali-Linux-2021.3-vbox-amd64",
                "os": "Debian (64-bit) / Kali",
                "state": "stopped",
                "ip": "192.168.56.10",
                "mac": "08:00:27:14:C8:91",
                "cpus": 4,
                "ram": 4096,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Penetration Testing Station",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "kali_redteam_preview.png"
            },
            "win7-copy-03": {
                "id": "e8b15b30-2864-4fdd-b183-e9746be4887b",
                "name": "Win7 1",
                "os": "Windows 7 (64-bit)",
                "state": "stopped",
                "ip": "192.168.56.102",
                "mac": "08:00:27:E8:B1:5B",
                "cpus": 2,
                "ram": 2048,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Cloned Student Machine",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "win2022_dc_preview.png"
            },
            "kali-2026-run-04": {
                "id": "a90184b2-3819-4501-8172-1149e917d004",
                "name": "kali-linux-2026.2-virtualbox-amd64",
                "os": "Debian (64-bit) / Kali Rolling",
                "state": "running",
                "ip": "192.168.56.11",
                "mac": "08:00:27:A9:01:84",
                "cpus": 4,
                "ram": 4096,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Active Offensive Assailant",
                "is_simulated": True,
                "uptime": "1h 45m",
                "screenshot": "kali_redteam_preview.png"
            },
            "csal231-05": {
                "id": "b11295c3-4920-5612-9283-2250fa28e005",
                "name": "csal231",
                "os": "Ubuntu 22.04 LTS (64-bit)",
                "state": "stopped",
                "ip": "192.168.56.25",
                "mac": "08:00:27:B1:12:95",
                "cpus": 2,
                "ram": 4096,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Offensive Security Lab Node",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "splunk_soc_preview.png"
            },
            "cfmba-final-06": {
                "id": "c223a6d4-5031-6723-a394-3361fb39f006",
                "name": "CFMBA_FinalChallenge",
                "os": "Linux 64-bit",
                "state": "stopped",
                "ip": "192.168.56.60",
                "mac": "08:00:27:C2:23:A6",
                "cpus": 2,
                "ram": 2048,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Final Project Challenge Server",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "meta3_preview.png"
            },
            "cfmba-final-1-07": {
                "id": "d334b7e5-6142-7834-b4a5-44720c4a0007",
                "name": "CFMBA_FinalChallenge 1",
                "os": "Linux 64-bit",
                "state": "stopped",
                "ip": "192.168.56.61",
                "mac": "08:00:27:D3:34:B7",
                "cpus": 2,
                "ram": 2048,
                "net_mode": "NAT Network (Lab environment)",
                "role": "Challenge Target Node 2",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "meta3_preview.png"
            },
            "splunk-soc-08": {
                "id": "e445c8f6-7253-8945-c5b6-55831d5b1008",
                "name": "Splunk-SOC-Collector",
                "os": "Ubuntu 22.04 LTS (64-bit)",
                "state": "running",
                "ip": "192.168.56.20",
                "mac": "08:00:27:E4:45:C8",
                "cpus": 4,
                "ram": 8192,
                "net_mode": "Host-Only (vboxnet0)",
                "role": "SIEM & Threat Telemetry Collector",
                "is_simulated": True,
                "uptime": "5h 12m",
                "screenshot": "splunk_soc_preview.png"
            },
            "win2022-dc-09": {
                "id": "f556d907-8364-9056-d6c7-66942e6c2009",
                "name": "WinServer-2022-AD-DC",
                "os": "Windows Server 2022 (64-bit)",
                "state": "stopped",
                "ip": "192.168.56.50",
                "mac": "08:00:27:F5:56:D9",
                "cpus": 2,
                "ram": 6144,
                "net_mode": "Host-Only (vboxnet0)",
                "role": "Active Directory Domain Controller",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "win2022_dc_preview.png"
            },
            "remnux-010": {
                "id": "0667ea18-9475-0167-e7d8-77053f7d3010",
                "name": "Remnux-Malware-Sandbox",
                "os": "Ubuntu 20.04 (64-bit) / Remnux",
                "state": "stopped",
                "ip": "192.168.56.30",
                "mac": "08:00:27:06:67:EA",
                "cpus": 2,
                "ram": 4096,
                "net_mode": "Internal (isolated_sandbox)",
                "role": "Reverse Engineering & Dynamic Analysis",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "remnux_sandbox_preview.png"
            },
            "meta3-011": {
                "id": "1778fb29-0586-1278-f8e9-8816408e4011",
                "name": "Metasploitable3-Vuln-Target",
                "os": "Ubuntu 14.04 (64-bit)",
                "state": "stopped",
                "ip": "192.168.56.99",
                "mac": "08:00:27:17:78:FB",
                "cpus": 1,
                "ram": 2048,
                "net_mode": "Host-Only (vboxnet0)",
                "role": "CTF Target / Honeypot",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "meta3_preview.png"
            },
            "student-01-vm": {"id": "28890c3a-1697-2389-09fa-9927519f5012", "name": "Lab - User 1", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.111", "mac": "08:00:27:28:89:0C", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-02-vm": {"id": "399a1d4b-2708-3490-1a0b-aa3862a06013", "name": "Lab - User 2", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.112", "mac": "08:00:27:39:9A:1D", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-03-vm": {"id": "4aab2e5c-3819-4501-2b1c-bb4973b17014", "name": "Lab - User 3", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.113", "mac": "08:00:27:4A:AB:2E", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-04-vm": {"id": "5bbc3f6d-4920-5612-3c2d-cc5a84c28015", "name": "Lab - User 4", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.114", "mac": "08:00:27:5B:BC:3F", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-05-vm": {"id": "6ccd407e-5031-6723-4d3e-dd6b95d39016", "name": "Lab - User 5", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.115", "mac": "08:00:27:6C:CD:40", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-06-vm": {"id": "7dde518f-6142-7834-5e4f-ee7ca6e4a017", "name": "Lab - User 6", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.116", "mac": "08:00:27:7D:DE:51", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-07-vm": {"id": "8eef6290-7253-8945-6f50-ff8db7f5b018", "name": "Lab - User 7", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.117", "mac": "08:00:27:8E:EF:62", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-08-vm": {"id": "9ff073a1-8364-9056-7061-009ec806c019", "name": "Lab - User 8", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.118", "mac": "08:00:27:9F:F0:73", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-09-vm": {"id": "a00184b2-9475-0167-8172-11afda17d020", "name": "Lab - User 9", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.119", "mac": "08:00:27:A0:01:84", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"},
            "student-10-vm": {"id": "b11295c3-0586-1278-9283-22b0eb28e021", "name": "Lab - User 10", "os": "Windows 10", "state": "stopped", "ip": "192.168.56.120", "mac": "08:00:27:B1:12:95", "cpus": 2, "ram": 4096, "net_mode": "NAT Network", "role": "Student Station", "is_simulated": True, "uptime": "0m"}
        }
        self._ensure_preview_images()

    def invalidate_vm_cache(self):
        """Invalidates the in-memory VM cache on any mutation"""
        self._vm_cache = None

    def _ensure_preview_images(self):
        """Pre-generate authentic looking screenshots for initial simulated lab VMs"""
        screens = [
            ("splunk_soc_preview.png", "Splunk Enterprise - Security Operations Center", [
                "[SOC-DASHBOARD] Threat Intel Stream Connected",
                "Events Indexed (last 1h): 48,219 events/sec",
                "Alerts Triggered: [CRITICAL] Anomaly on DC-03 - Kerberoasting attempt",
                "Source: 192.168.56.10 (Kali-Linux-RedTeam)",
                "Target: 192.168.56.50:88 (Kerberos Auth Service)",
                "Mitigation Action: Flagged for Operator Isolation"
            ], (0, 255, 157)),
            ("win2022_dc_preview.png", "Windows Server 2022 Datacenter - [CORP.CYBERLAB]", [
                "Server Manager - Dashboard Active",
                "Active Directory Domain Services: ONLINE (corp.cyberlab.local)",
                "DNS Server: ACTIVE | DHCP Pool: 192.168.56.100 - 192.168.56.200",
                "Security Audit Log: Event ID 4625 (Failed Logon - User: Administrator)",
                "Workstation: KALI-ATTACKER (192.168.56.10)",
                "Status: Policy Enforcement Active - Account Lockout Threshold: 5"
            ], (0, 150, 255)),
            ("remnux_sandbox_preview.png", "REMnux Linux - Dynamic Malware Analysis", [
                "remnux@sandbox:~# inetsim --version",
                "INetSim 1.3.2 (Simulated Internet Services for Malware Analysis)",
                "Listening on: DNS (53), HTTP (80), HTTPS (443), SMTP (25)",
                "C2 Beacon Caught: GET /beacon.php?id=a8f92b HTTP/1.1",
                "Host: evil-command-control.darknet.test (192.168.56.30)",
                "Sandbox Isolation: [SECURE] Network egress blocked."
            ], (255, 180, 0)),
            ("meta3_preview.png", "Metasploitable3 - Target Appliance", [
                "Metasploitable3 login: _ (System Offline / Power Suspended)",
                "Services pre-configured: SMB, SSH, FTP, Apache, MySQL, WebDAV",
                "Target Status: Ready for Red Team penetration testing exercise.",
                "Press 'Start VM' to boot target and open attack surface."
            ], (150, 150, 160))
        ]

        for fname, title, lines, color in screens:
            fpath = os.path.join(self.screenshots_dir, fname)
            if not os.path.exists(fpath):
                self._draw_mock_screen(fpath, title, lines, color)

    def _draw_mock_screen(self, fpath, title, lines, accent_color):
        if not HAS_PIL:
            with open(fpath, 'wb') as f:
                f.write(FALLBACK_PNG)
            return
        img = Image.new('RGB', (1280, 720), color=(10, 15, 24))
        draw = ImageDraw.Draw(img)
        # Window bar
        draw.rectangle([(0,0), (1280, 36)], fill=(18, 26, 40))
        draw.ellipse([(14, 12), (24, 22)], fill=(255, 95, 87))
        draw.ellipse([(32, 12), (42, 22)], fill=(254, 187, 43))
        draw.ellipse([(50, 12), (60, 22)], fill=(39, 201, 63))
        draw.text((80, 10), title, fill=(200, 220, 240))

        # Cyber frame
        draw.rectangle([(10, 46), (1270, 710)], outline=(30, 45, 65), width=1)

        y = 70
        draw.text((30, y), f"[CYBERLAB HUD SURVEILLANCE] // LIVE FEED :: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=accent_color)
        y += 40

        for line in lines:
            col = (220, 235, 255)
            if "CRITICAL" in line or "Failed" in line or "evil" in line:
                col = (255, 51, 102)
            elif "ONLINE" in line or "ACTIVE" in line or "SECURE" in line or "Connected" in line:
                col = (0, 255, 157)
            elif "Warning" in line or "Alert" in line or "Offline" in line:
                col = (255, 184, 0)
            draw.text((30, y), line, fill=col)
            y += 32

        img.save(fpath)

    def _run_vbox_cmd(self, args):
        if not self.vbox_bin:
            return {"success": False, "stdout": "", "stderr": "vboxmanage binary not found on host."}
        try:
            cmd = [self.vbox_bin] + args
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": (res.returncode == 0),
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

    def list_real_vms(self):
        """Runs: vboxmanage list vms"""
        res = self._run_vbox_cmd(["list", "vms"])
        vms = []
        if res["success"]:
            # Format: "VM Name" {uuid}
            pattern = re.compile(r'"([^"]+)"\s+\{([^}]+)\}')
            for match in pattern.finditer(res["stdout"]):
                name, uuid = match.groups()
                vms.append({
                    "id": uuid,
                    "name": name,
                    "uuid": uuid,
                    "is_simulated": False
                })
        return vms

    def list_real_running_vms(self):
        """Runs: vboxmanage list runningvms"""
        res = self._run_vbox_cmd(["list", "runningvms"])
        running = set()
        if res["success"]:
            pattern = re.compile(r'"([^"]+)"\s+\{([^}]+)\}')
            for match in pattern.finditer(res["stdout"]):
                name, uuid = match.groups()
                running.add(uuid)
                running.add(name)
        return running

    def get_real_vm_ip(self, vmid):
        """Runs: vboxmanage guestproperty get $vmid "/VirtualBox/GuestInfo/Net/0/V4/IP" """
        res = self._run_vbox_cmd(["guestproperty", "get", vmid, "/VirtualBox/GuestInfo/Net/0/V4/IP"])
        if res["success"] and "Value:" in res["stdout"]:
            # Value: 192.168.x.x
            parts = res["stdout"].split("Value:")
            if len(parts) > 1:
                return parts[1].strip()
        # Fallback check adapter 1
        res1 = self._run_vbox_cmd(["guestproperty", "get", vmid, "/VirtualBox/GuestInfo/Net/1/V4/IP"])
        if res1["success"] and "Value:" in res1["stdout"]:
            parts = res1["stdout"].split("Value:")
            if len(parts) > 1:
                return parts[1].strip()
        return "Unknown / Guest Tools Pending"

    def get_real_vm_details(self, vmid):
        """Runs: vboxmanage showvminfo $vmid --machinereadable"""
        res = self._run_vbox_cmd(["showvminfo", vmid, "--machinereadable"])
        details = {
            "cpus": 1,
            "ram": 1024,
            "os": "Unknown OS",
            "net_mode": "NAT",
            "mac": "N/A",
            "state": "stopped"
        }
        if res["success"]:
            for line in res["stdout"].splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"')
                    if k == "cpus":
                        details["cpus"] = int(v) if v.isdigit() else 1
                    elif k == "memory":
                        details["ram"] = int(v) if v.isdigit() else 1024
                    elif k == "ostype":
                        details["os"] = v
                    elif k == "VMState":
                        details["state"] = "running" if v == "running" else ("paused" if v == "paused" else "stopped")
                    elif k == "nic1":
                        details["net_mode"] = v
                    elif k == "macaddress1":
                        # Format 0800271A3B5C into colon format
                        if len(v) == 12:
                            details["mac"] = ":".join(v[i:i+2] for i in range(0, 12, 2))
                        else:
                            details["mac"] = v
        return details

    def get_all_vms(self):
        """Returns unified list of real VMs and simulated cyber range VMs with 3-sec caching"""
        now = time.time()
        if self._vm_cache is not None and (now - self._vm_cache_time < self._cache_ttl):
            return [dict(v) for v in self._vm_cache]

        real_vms = self.list_real_vms()
        running_set = self.list_real_running_vms() if real_vms else set()

        combined = []

        # Process real VMs first
        for vm in real_vms:
            vmid = vm["id"]
            name = vm["name"]
            is_running = (vmid in running_set or name in running_set)
            details = self.get_real_vm_details(vmid)
            ip = self.get_real_vm_ip(vmid) if is_running else "Offline"
            
            combined.append({
                "id": vmid,
                "name": name,
                "os": details["os"],
                "state": "running" if is_running else details["state"],
                "ip": ip,
                "mac": details["mac"],
                "cpus": details["cpus"],
                "ram": details["ram"],
                "net_mode": details["net_mode"],
                "role": "Host Virtual Machine",
                "is_simulated": False,
                "uptime": "Active" if is_running else "0m",
                "screenshot": None
            })

        # Add simulated Cyber Range VMs if demo_enabled or if 0 real VMs exist
        if self.demo_enabled or len(combined) == 0:
            for k, vm in self.simulated_vms.items():
                combined.append(dict(vm))

        self._vm_cache = combined
        self._vm_cache_time = now
        return combined

    def get_vm_by_id(self, vmid):
        all_vms = self.get_all_vms()
        for vm in all_vms:
            if vm["id"] == vmid or vm["name"] == vmid:
                return vm
        return None

    def start_vm(self, vmid, headless=True):
        """Starts real or simulated VM"""
        self.invalidate_vm_cache()
        # Check simulated first
        for k, vm in self.simulated_vms.items():
            if vm["id"] == vmid or vm["name"] == vmid:
                vm["state"] = "running"
                vm["uptime"] = "Just booted (0m)"
                return {"success": True, "message": f"CyberLab VM '{vm['name']}' booted successfully (Simulation Mode).", "state": "running"}

        # Real VM
        vm_type = "headless" if headless else "gui"
        res = self._run_vbox_cmd(["startvm", vmid, "--type", vm_type])
        if res["success"]:
            return {"success": True, "message": f"VM '{vmid}' launched successfully via vboxmanage ({vm_type}).", "output": res["stdout"]}
        else:
            return {"success": False, "message": f"Failed to start VM: {res['stderr']}", "error": res["stderr"]}

    def stop_vm(self, vmid, force=False):
        """Stops real or simulated VM"""
        self.invalidate_vm_cache()
        for k, vm in self.simulated_vms.items():
            if vm["id"] == vmid or vm["name"] == vmid:
                vm["state"] = "stopped"
                vm["uptime"] = "0m"
                return {"success": True, "message": f"CyberLab VM '{vm['name']}' halted successfully.", "state": "stopped"}

        action = "poweroff" if force else "acpipowerbutton"
        res = self._run_vbox_cmd(["controlvm", vmid, action])
        if not res["success"] and not force:
            # ACPI might fail, try poweroff
            res = self._run_vbox_cmd(["controlvm", vmid, "poweroff"])
        
        if res["success"]:
            return {"success": True, "message": f"VM '{vmid}' stopped successfully.", "output": res["stdout"]}
        else:
            return {"success": False, "message": f"Failed to stop VM: {res['stderr']}", "error": res["stderr"]}

    def pause_vm(self, vmid):
        for k, vm in self.simulated_vms.items():
            if vm["id"] == vmid or vm["name"] == vmid:
                new_state = "running" if vm["state"] == "paused" else "paused"
                vm["state"] = new_state
                return {"success": True, "message": f"VM '{vm['name']}' state changed to {new_state}.", "state": new_state}

        # Check current state for real VM
        res = self._run_vbox_cmd(["controlvm", vmid, "pause"])
        if not res["success"]:
            res = self._run_vbox_cmd(["controlvm", vmid, "resume"])
        return {"success": res["success"], "message": res["stdout"] or res["stderr"]}

    def take_screenshot(self, vmid):
        """Matches user's takescreenvm.sh: vboxmanage controlvm $vmid screenshotpng $capturen"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{vmid[:8]}_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)

        # Check simulated
        for k, vm in self.simulated_vms.items():
            if vm["id"] == vmid or vm["name"] == vmid:
                # Generate a real fresh screenshot image for this VM
                self._generate_dynamic_screenshot(filepath, vm)
                vm["screenshot"] = filename
                return {
                    "success": True,
                    "filename": filename,
                    "url": f"/static/screenshots/{filename}",
                    "timestamp": timestamp,
                    "vm_name": vm["name"]
                }

        # Clean up older screenshots to enforce 50 max files limit
        self._cleanup_old_screenshots(max_keep=50)

        # Real VM
        res = self._run_vbox_cmd(["controlvm", vmid, "screenshotpng", filepath])
        if res["success"] and os.path.exists(filepath):
            self._cleanup_old_screenshots(max_keep=50)
            return {
                "success": True,
                "filename": filename,
                "url": f"/static/screenshots/{filename}",
                "timestamp": timestamp,
                "vm_name": vmid
            }
        else:
            return {
                "success": False,
                "message": f"Screenshot failed: {res['stderr'] or 'VM must be running to capture screenshot.'}",
                "error": res["stderr"]
            }

    def _cleanup_old_screenshots(self, max_keep=50):
        """Enforces a retention limit of 50 screenshots to prevent disk exhaustion"""
        try:
            files = [
                os.path.join(self.screenshots_dir, f)
                for f in os.listdir(self.screenshots_dir)
                if f.startswith("screenshot_") and f.endswith(('.png', '.jpg', '.webp'))
            ]
            if len(files) > max_keep:
                files.sort(key=lambda x: os.path.getmtime(x))
                to_delete = files[:len(files) - max_keep]
                for f in to_delete:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
        except Exception:
            pass

    def _generate_dynamic_screenshot(self, filepath, vm):
        """Generates realistic live capture for a simulated VM"""
        if not HAS_PIL:
            with open(filepath, 'wb') as f:
                f.write(FALLBACK_PNG)
            return
        img = Image.new('RGB', (1280, 720), color=(10, 15, 24))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0,0), (1280, 36)], fill=(18, 26, 40))
        draw.ellipse([(14, 12), (24, 22)], fill=(255, 95, 87))
        draw.ellipse([(32, 12), (42, 22)], fill=(254, 187, 43))
        draw.ellipse([(50, 12), (60, 22)], fill=(39, 201, 63))
        draw.text((80, 10), f"{vm['name']} - [LIVE VIRTUAL DISPLAY: DISPLAY 0]", fill=(200, 225, 255))

        draw.rectangle([(10, 46), (1270, 710)], outline=(0, 240, 255), width=1)

        draw.text((30, 60), f"[*] CFMBA SURVEILLANCE FEED CAPTURE - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST (Israel)')}", fill=(0, 240, 255))
        draw.text((30, 90), f"[*] TARGET UUID: {vm['id']} | IP: {vm['ip']} | MAC: {vm['mac']}", fill=(0, 255, 157))
        draw.text((30, 120), f"[*] OS: {vm['os']} | CPU Cores: {vm['cpus']} | RAM: {vm['ram']} MB", fill=(255, 184, 0))

        # Terminal lines
        if "Kali" in vm["name"]:
            draw.text((30, 170), "kali@cyberlab:~$ sudo wireshark -k -i eth0 &", fill=(220, 220, 220))
            draw.text((30, 200), "Capturing on 'eth0'... 14,290 packets analyzed.", fill=(0, 255, 157))
            draw.text((30, 230), "kali@cyberlab:~$ hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.56.50 smb", fill=(220, 220, 220))
            draw.text((30, 260), "[DATA] Attack module active. Target port 445 open.", fill=(255, 51, 102))
        elif "Splunk" in vm["name"]:
            draw.text((30, 170), "[SPLUNK-FORWARDER] Listening on port 9997 (TLS Encrypted)", fill=(0, 255, 157))
            draw.text((30, 200), "[SECURITY-AUDIT] Ingestion rate: 3.4 MB/s from lab subnet 192.168.56.0/24", fill=(220, 220, 220))
            draw.text((30, 230), "[ALERT-DISPATCH] CyberLab SIEM Dashboard synchronized.", fill=(0, 240, 255))
        elif "Win" in vm["name"]:
            draw.text((30, 170), "C:\\Windows\\system32> whoami /priv", fill=(220, 220, 220))
            draw.text((30, 200), "SeSecurityPrivilege            Manage auditing and security log      Enabled", fill=(0, 255, 157))
            draw.text((30, 230), "SeBackupPrivilege              Back up files and directories         Enabled", fill=(220, 220, 220))
            draw.text((30, 260), "C:\\Windows\\system32> net user /domain", fill=(220, 220, 220))
        else:
            draw.text((30, 170), f"Virtual Machine console active for {vm['name']}.", fill=(220, 220, 220))
            draw.text((30, 200), "Kernel: Linux 6.8.0-generic x86_64", fill=(0, 240, 255))
            draw.text((30, 230), "Network: Connected to VirtualBox Host-Only Adapter.", fill=(0, 255, 157))

        draw.text((30, 660), "[STATUS: OPERATIONAL] VirtualBox Guest Additions Active. Hardware acceleration: Enabled.", fill=(120, 140, 170))
        img.save(filepath)

    def import_ova(self, ova_path, vm_name=None, cpus=None, ram=None):
        """Matches user's importvm.sh: vboxmanage import $vmname"""
        self.invalidate_vm_cache()
        if not os.path.exists(ova_path):
            return {"success": False, "message": f"OVA file '{ova_path}' does not exist."}

        # Build args
        args = ["import", ova_path]
        if vm_name:
            args.extend(["--vsys", "0", "--vmname", vm_name])
        if cpus:
            args.extend(["--vsys", "0", "--cpus", str(cpus)])
        if ram:
            args.extend(["--vsys", "0", "--memory", str(ram)])

        if self.vbox_bin:
            res = self._run_vbox_cmd(args)
            if res["success"]:
                return {"success": True, "message": f"Appliance '{os.path.basename(ova_path)}' imported into VirtualBox successfully!", "output": res["stdout"]}
            else:
                # If host error, provide simulation fallback
                return {"success": False, "message": f"VirtualBox import returned: {res['stderr']}", "error": res["stderr"]}
        else:
            # Simulated import
            new_id = f"custom-import-{int(time.time())}"
            target_name = vm_name or os.path.splitext(os.path.basename(ova_path))[0]
            self.simulated_vms[new_id] = {
                "id": new_id,
                "name": target_name,
                "os": "Linux / Custom OVA Appliance",
                "state": "stopped",
                "ip": "192.168.56.75",
                "mac": "08:00:27:77:88:99",
                "cpus": int(cpus) if cpus else 2,
                "ram": int(ram) if ram else 4096,
                "net_mode": "Host-Only (vboxnet0)",
                "role": "Imported Lab Appliance",
                "is_simulated": True,
                "uptime": "0m",
                "screenshot": "kali_redteam_preview.png"
            }
            return {"success": True, "message": f"Appliance '{target_name}' imported successfully into CyberLab fleet (Simulation Mode)."}

    def clone_vm(self, source_id, new_name, copy_state="current", start_after=False):
        """Matches Screenshot 2: Duplicate a VM (clonevm)"""
        self.invalidate_vm_cache()
        mode = "all" if copy_state == "all" else "machine"
        if self.vbox_bin:
            res = self._run_vbox_cmd(["clonevm", source_id, "--name", new_name, "--register", "--mode", mode])
            if res["success"]:
                if start_after:
                    self.start_vm(new_name)
                return {"success": True, "message": f"Successfully cloned '{new_name}' from '{source_id}'."}
            return {"success": False, "message": f"Clone failed: {res['stderr']}"}
        
        # Simulation
        new_id = f"clone-{int(time.time())}"
        self.simulated_vms[new_id] = {
            "id": new_id,
            "name": new_name,
            "os": "Windows / Linux (Cloned)",
            "state": "running" if start_after else "stopped",
            "ip": "192.168.56.88",
            "mac": "08:00:27:AA:BB:CC",
            "cpus": 2,
            "ram": 4096,
            "net_mode": "NAT Network (Lab environment)",
            "role": "Duplicated User Machine",
            "is_simulated": True,
            "uptime": "Just booted (0m)" if start_after else "0m",
            "screenshot": "win2022_dc_preview.png"
        }
        return {"success": True, "message": f"VM '{new_name}' duplicated successfully{' and started' if start_after else ''}."}

    def create_vm(self, name, ostype="Debian_64", memory_mb=4096, cpus=2, vdi_mb=81920, iso=None):
        """Matches Screenshot 3: Create a new machine"""
        self.invalidate_vm_cache()
        if self.vbox_bin:
            res = self._run_vbox_cmd(["createvm", "--name", name, "--ostype", ostype, "--register"])
            if res["success"]:
                self._run_vbox_cmd(["modifyvm", name, "--memory", str(memory_mb), "--cpus", str(cpus), "--nic1", "natnetwork", "--nat-network1", "NatNetwork"])
                return {"success": True, "message": f"Virtual Machine '{name}' created and registered successfully!"}
            return {"success": False, "message": f"Failed to create VM: {res['stderr']}"}

        new_id = f"create-{int(time.time())}"
        self.simulated_vms[new_id] = {
            "id": new_id,
            "name": name,
            "os": ostype,
            "state": "stopped",
            "ip": "192.168.56.77",
            "mac": "08:00:27:11:22:33",
            "cpus": int(cpus) if str(cpus).isdigit() else 2,
            "ram": int(memory_mb) if str(memory_mb).isdigit() else 2048,
            "net_mode": "NAT Network",
            "role": "Newly Provisioned System",
            "is_simulated": True,
            "uptime": "0m",
            "screenshot": "kali_redteam_preview.png"
        }
        return {"success": True, "message": f"Virtual machine '{name}' provisioned and registered in fleet."}

    def register_vm(self, vbox_path):
        """Matches Screenshot 3: Register existing machine"""
        self.invalidate_vm_cache()
        if not vbox_path.strip().endswith(".vbox"):
            return {"success": False, "message": "File path must end with .vbox"}
        if self.vbox_bin:
            res = self._run_vbox_cmd(["registervm", vbox_path.strip()])
            if res["success"]:
                return {"success": True, "message": f"Machine at '{vbox_path}' registered successfully."}
            return {"success": False, "message": f"Register failed: {res['stderr']}"}

        vm_name = os.path.splitext(os.path.basename(vbox_path.strip()))[0]
        new_id = f"reg-{int(time.time())}"
        self.simulated_vms[new_id] = {
            "id": new_id,
            "name": vm_name,
            "os": "Imported .vbox",
            "state": "stopped",
            "ip": "192.168.56.90",
            "mac": "08:00:27:44:55:66",
            "cpus": 2,
            "ram": 4096,
            "net_mode": "Host-Only",
            "role": "Registered Existing Machine",
            "is_simulated": True,
            "uptime": "0m",
            "screenshot": "meta3_preview.png"
        }
        return {"success": True, "message": f"Existing machine '{vm_name}' registered successfully."}

    def get_extpacks(self):
        """Matches Screenshot 3: Extension packs output"""
        if self.vbox_bin:
            res = self._run_vbox_cmd(["list", "extpacks"])
            if res["success"] and len(res["stdout"].strip()) > 20:
                return res["stdout"]
        # Supervisor reference display
        return (
            "Extension Packs: 1\n"
            "Pack no. 0:   Oracle VM VirtualBox Extension Pack\n"
            "Version:      6.1.34\n"
            "Revision:     150636\n"
            "Edition:      \n"
            "Description:  Oracle Cloud Infrastructure integration, USB 2.0 and USB 3.0 Host Controller, "
            "Host Webcam, VirtualBox RDP, PXE ROM, Disk Encryption, NVMe.\n"
            "VRDE Module:  VBoxVRDP\n"
            "Crypto Module: \n"
            "Usable:       false\n"
            "Why unusable: VBoxExtPackRegister returned VERR_VERSION_MISMATCH, "
            "pAop=0000000000000000 ErrInfo='Helper version mismatch - expected 0x30000 got 0x50000'"
        )

    def launch_scenario(self, scenario_name, network_mode, selected_vm_ids):
        """Matches Screenshot 2: Batch Start Scenarios"""
        started = []
        failed = []
        for vmid in selected_vm_ids:
            res = self.start_vm(vmid)
            if res.get("success"):
                started.append(vmid)
            else:
                failed.append(vmid)
        msg = f"Scenario '{scenario_name}' launched on {network_mode}: {len(started)} systems started."
        if failed:
            msg += f" ({len(failed)} failed)"
        return {"success": True, "message": msg, "started": started, "failed": failed}
