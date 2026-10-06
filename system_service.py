import subprocess
import shutil
import psutil
import socket
import os
import platform
import time
import shlex

class SystemService:
    def __init__(self):
        self.boot_time = psutil.boot_time()
        self._df_cache = None
        self._df_cache_time = 0
        # Warm up cpu_percent non-blocking
        psutil.cpu_percent(interval=None)

    def get_df_h(self):
        """Runs the exact bash command `df -h` with 3-second caching for high performance"""
        now = time.time()
        if self._df_cache and (now - self._df_cache_time < 3.0):
            return self._df_cache

        try:
            res = subprocess.run(["df", "-h"], capture_output=True, text=True, timeout=5)
            raw = res.stdout
        except Exception as e:
            raw = f"Error running df -h: {e}"

        disks = []
        lines = raw.strip().splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    filesystem = parts[0]
                    size = parts[1]
                    used = parts[2]
                    avail = parts[3]
                    capacity_str = parts[4]
                    try:
                        capacity_num = int(capacity_str.replace('%', ''))
                    except ValueError:
                        capacity_num = 0
                    mounted_on = " ".join(parts[5:]) if len(parts) >= 6 else parts[5]
                    
                    is_primary = mounted_on in ["/", "/home", "/System/Volumes/Data"] or any(
                        filesystem.startswith(p) for p in ["/dev/disk", "/dev/sd", "/dev/nvme", "/dev/vd", "/dev/mapper"]
                    )
                    disks.append({
                        "filesystem": filesystem,
                        "size": size,
                        "used": used,
                        "avail": avail,
                        "capacity": capacity_str,
                        "capacity_num": capacity_num,
                        "mounted_on": mounted_on,
                        "is_primary": is_primary
                    })

        root_usage = psutil.disk_usage('/')
        result = {
            "raw": raw,
            "disks": disks,
            "summary": {
                "total_gb": round(root_usage.total / (1024**3), 1),
                "used_gb": round(root_usage.used / (1024**3), 1),
                "free_gb": round(root_usage.free / (1024**3), 1),
                "percent": root_usage.percent
            }
        }
        self._df_cache = result
        self._df_cache_time = now
        return result

    def get_system_telemetry(self):
        """Live CPU, RAM, and Host metrics (non-blocking for fast telemetry)"""
        # interval=None returns instantaneous CPU since last call without 100ms blocking
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        uptime_seconds = int(time.time() - self.boot_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60

        return {
            "cpu_percent": cpu_pct,
            "cpu_cores": psutil.cpu_count(logical=True),
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "free_gb": round(mem.free / (1024**3), 2),
                "percent": mem.percent
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "percent": swap.percent
            },
            "uptime": f"{hours}h {minutes}m",
            "host_os": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "hostname": socket.gethostname()
        }

    def test_connectivity(self, target_ip, port=None):
        """Tests ping or TCP connection to VM"""
        if port:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                start = time.time()
                res = s.connect_ex((target_ip, int(port)))
                latency = round((time.time() - start) * 1000, 2)
                s.close()
                return {
                    "ip": target_ip,
                    "port": port,
                    "open": (res == 0),
                    "latency_ms": latency if res == 0 else None,
                    "status": "OPEN" if res == 0 else "CLOSED / FILTERED"
                }
            except Exception as e:
                return {"ip": target_ip, "port": port, "open": False, "status": f"Error: {e}"}

        try:
            cmd = ["ping", "-c", "2", "-W", "1500", target_ip]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            is_up = (res.returncode == 0)
            return {
                "ip": target_ip,
                "reachable": is_up,
                "output": res.stdout or res.stderr,
                "status": "ONLINE (Host Responsive)" if is_up else "OFFLINE / UNREACHABLE"
            }
        except Exception as e:
            return {"ip": target_ip, "reachable": False, "status": f"Error: {e}"}

    def execute_terminal_cmd(self, command):
        """Executes safe lab and diagnostic commands without shell=True to prevent command injection"""
        cmd_clean = (command or "").strip()
        if not cmd_clean:
            return {"success": False, "output": "Empty command provided."}

        # 1. Strict blocking of shell chaining and redirection metacharacters
        dangerous_metachars = [";", "|", "&", "$", "`", "\\", "(", ")", ">", "<", "\n", "\r"]
        for ch in dangerous_metachars:
            if ch in cmd_clean:
                return {
                    "success": False,
                    "output": f"[SECURITY POLICY VIOLATION] Shell metacharacter '{ch}' is strictly forbidden."
                }

        # 2. Parse command securely into arguments list
        try:
            tokens = shlex.split(cmd_clean)
        except Exception as e:
            return {"success": False, "output": f"[SYNTAX ERROR] Failed to parse command: {e}"}

        if not tokens:
            return {"success": False, "output": "Empty command provided."}

        binary = tokens[0]

        # 3. Explicit whitelist of allowed system tools (Notice 'cat' removed to prevent credential exposure)
        allowed_binaries = {
            "df", "vboxmanage", "VBoxManage", "uptime", "uname", "whoami",
            "ps", "top", "netstat", "ifconfig", "ping", "ls", "echo", "pwd",
            "date", "id"
        }

        is_allowed = False
        if binary in allowed_binaries:
            is_allowed = True
        elif binary.startswith("./scripts/") or binary.startswith("scripts/"):
            # Ensure path does not traverse outside scripts/
            norm_path = os.path.normpath(binary)
            if (norm_path.startswith("scripts/") or norm_path.startswith("./scripts/")) and ".." not in norm_path:
                is_allowed = True

        if not is_allowed:
            return {
                "success": False,
                "output": f"[SECURITY POLICY VIOLATION] Command '{binary}' is not permitted. Only VirtualBox, system telemetry, and lab diagnostic commands are permitted."
            }

        # Block attempts to view sensitive files via arguments
        forbidden_targets = ["users.json", ".secret_key", "shadow", "passwd", "id_rsa"]
        for t in tokens[1:]:
            for f in forbidden_targets:
                if f in t.lower():
                    return {
                        "success": False,
                        "output": f"[SECURITY POLICY VIOLATION] Access to sensitive file '{f}' is restricted."
                    }

        # 4. Execute with shell=False for complete command injection immunity
        try:
            res = subprocess.run(tokens, shell=False, capture_output=True, text=True, timeout=15)
            output = res.stdout
            if res.stderr:
                output += ("\n[STDERR]\n" + res.stderr)
            return {
                "success": (res.returncode == 0),
                "output": output or "[Process completed with no output]",
                "returncode": res.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "[!] Command execution timed out after 15 seconds."}
        except FileNotFoundError:
            return {"success": False, "output": f"[!] Executable '{binary}' not found on host system."}
        except Exception as e:
            return {"success": False, "output": f"[!] Execution exception: {e}"}
