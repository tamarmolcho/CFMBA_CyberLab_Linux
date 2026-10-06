# CFMBA CyberLab Operations Center (CLOC) - Linux Edition
**Academic Cybersecurity Lab & Virtual Machine Management Platform**  
- **Developer / Student:** Tamar Molcho  
- **Academic Supervisor:** Mr. Jack Altal  
- **Institution:** Ono Academic College — Faculty of Computer Science & Information Systems  

---

## 🚀 Quick Start (One Command)

To launch the complete application:
```bash
./run.sh
```

The server will automatically start on:
👉 **http://127.0.0.1:5050** (or your server's IP address on port 5050).

*(Note: If Python system dependencies are missing on Debian/Ubuntu/Kali, run once: `sudo ./setup_kali.sh`).*

---

## 🔑 Pre-Configured Test Accounts (RBAC Demonstration)

| Role | Username | Password | Full Name | Access Level & Entitlements |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Tamar Molcho | Full unrestricted access to all modules, fleet operations, user creation/deletion, and granular permissions. |
| **Lecturer / Supervisor** | `jack` | `jack123` | Mr. Jack Altal | Lab management clearance: VM controls, lab scenarios, student creation & granular permission assignment. |
| **Active Student** | `dan` | `dan123` | Dan Cohen | Selective permissions demonstration: Authorized for Threat Drill Game & Surveillance feed only. |
| **Restricted Student** | `student` | `student123` | Cyber Lab Student | Zero permissions baseline: Demonstrates locked screen and 403 Forbidden until granted by Lecturer/Admin. |

---

## 🧪 Run Automated Quality Assurance Suite (Pytest)

Run the automated test suite directly in this directory:
```bash
python3 -m pytest tests/test_cyberlab.py -v
```
**Result:** **13 of 13 tests passing (100% Pass Rate)** validating authentication, RBAC boundaries, command injection prevention, and telemetry schemas.

---

## 📊 Entity Relationship Diagram (ERD) & Documentation

- **Live Interactive Viewer in App:** `http://127.0.0.1:5050/erd`
- **High-Resolution Diagram:** `docs/erd_diagram.png`
- **Standalone HTML Viewer:** `docs/erd_viewer.html`
- **Data Dictionary & Schema Spec:** `docs/ERD.md`

---

## 🛡️ Key Features & Capabilities
1. **VM Dashboard:** Real-time power states (start/stop/pause) and host resource gauges (CPU, RAM, Disk).
2. **Surveillance Module:** Live VM display frame stream with local Israel time watermark (`IST`).
3. **Cyber Console:** Whitelist-guarded diagnostics terminal neutralizing shell injection vectors.
4. **CyberCopilot AI:** Multilingual virtual assistant supporting Hebrew & English voice/text commands.
5. **Threat Drill Test:** Interactive incident response reflex drill with live CSV leaderboard tracking.
6. **Hybrid Cyber Range:** Runs against real VirtualBox installations or auto-activates high-fidelity simulation if VirtualBox is not present.
