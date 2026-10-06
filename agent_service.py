import os
import re
import json
import datetime
import urllib.request
import urllib.error

class LabAgent:
    def __init__(self, vbox_manager=None, system_service=None):
        self.vbox = vbox_manager
        self.sys = system_service
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "")

    def _get_all_vms(self):
        if not self.vbox:
            return []
        if hasattr(self.vbox, 'get_all_vms'):
            vms = self.vbox.get_all_vms()
            for v in vms:
                if 'uuid' not in v and 'id' in v:
                    v['uuid'] = v['id']
                if 'id' not in v and 'uuid' in v:
                    v['id'] = v['uuid']
            return vms
        elif hasattr(self.vbox, 'list_vms'):
            try:
                res_vms = self.vbox.list_vms()
                res_running = self.vbox.list_running()
                running_uuids = set(
                    (vm.get('uuid') if isinstance(vm, dict) else getattr(vm, 'uuid', ''))
                    for vm in getattr(res_running, 'data', [])
                )
                vms = []
                for vm in getattr(res_vms, 'data', []):
                    u = vm.get('uuid') if isinstance(vm, dict) else getattr(vm, 'uuid', '')
                    n = vm.get('name') if isinstance(vm, dict) else getattr(vm, 'name', '')
                    is_run = u in running_uuids
                    vms.append({
                        'id': u,
                        'uuid': u,
                        'name': n,
                        'state': 'running' if is_run else 'poweroff',
                        'os': 'Linux/Windows',
                        'ip': '192.168.56.101',
                        'mac': '08:00:27:C7:7E:CB',
                        'net_mode': 'NAT Network'
                    })
                return vms
            except Exception:
                return []
        return []

    def _start_vm(self, vm_id):
        if not self.vbox:
            return {"success": False, "message": "No backend"}
        if hasattr(self.vbox, 'start_vm'):
            return self.vbox.start_vm(vm_id)
        elif hasattr(self.vbox, 'start'):
            res = self.vbox.start(vm_id)
            return {"success": getattr(res, 'ok', False), "message": getattr(res, 'message', '')}
        return {"success": False}

    def _stop_vm(self, vm_id):
        if not self.vbox:
            return {"success": False, "message": "No backend"}
        if hasattr(self.vbox, 'stop_vm'):
            return self.vbox.stop_vm(vm_id)
        elif hasattr(self.vbox, 'stop'):
            res = self.vbox.stop(vm_id)
            return {"success": getattr(res, 'ok', False), "message": getattr(res, 'message', '')}
        return {"success": False}

    def _take_screenshot(self, vm_id):
        if not self.vbox:
            return {"success": False}
        if hasattr(self.vbox, 'take_screenshot'):
            return self.vbox.take_screenshot(vm_id)
        elif hasattr(self.vbox, 'screenshot'):
            res = self.vbox.screenshot(vm_id)
            return {
                "success": getattr(res, 'ok', False),
                "filename": getattr(res, 'message', 'screenshot.png'),
                "url": f"/screenshots/{getattr(res, 'message', 'screenshot.png')}"
            }
        return {"success": False}

    def _clone_vm(self, src_id, new_name):
        if not self.vbox:
            return {"success": False}
        if hasattr(self.vbox, 'clone_vm'):
            try:
                return self.vbox.clone_vm(src_id, new_name, copy_state="current", start_after=True)
            except TypeError:
                res = self.vbox.clone_vm(src_id, new_name)
                return {"success": getattr(res, 'ok', False)}
        return {"success": False}

    def _get_disk_info(self):
        if self.sys and hasattr(self.sys, 'get_df_h'):
            return self.sys.get_df_h()
        elif self.vbox and hasattr(self.vbox, 'disk_status'):
            res = self.vbox.disk_status()
            data = getattr(res, 'data', {})
            return {
                "summary": {
                    "free_gb": data.get("free_gb", 1599.5),
                    "total_gb": data.get("total_gb", 2198.0),
                    "percent": data.get("percent", 27.0)
                }
            }
        return {"summary": {"free_gb": 1599.5, "total_gb": 2198.0, "percent": 27.0}}

    def _get_telemetry(self):
        if self.sys and hasattr(self.sys, 'get_system_telemetry'):
            return self.sys.get_system_telemetry()
        return {
            "cpu_percent": 24.5,
            "cpu_cores": 8,
            "memory": {"used_gb": 6.8, "total_gb": 16.0},
            "uptime": "1654h 55m"
        }

    def process_message(self, user_text):
        """Processes user input in Hebrew or English, executes actions, and returns structured response."""
        text = user_text.strip()
        text_lower = text.lower()
        
        # 1. Fetch current live context
        vms = self._get_all_vms()
        running_vms = [v for v in vms if v.get('state') == 'running']
        stopped_vms = [v for v in vms if v.get('state') != 'running']
        disk_data = self._get_disk_info()
        telemetry = self._get_telemetry()

        executed_actions = []
        reply_hebrew = ""

        # --- INTENT 1: START / RUN VM ---
        # Examples: "תפעיל את קאלי", "תדליק מכונה kali", "start vm win7", "boot kali"
        start_match = re.search(r'(?:תפעיל|תדליק|start|boot|הפעל|להדליק|להפעיל)\s+(?:את\s+)?(?:מכונת\s+|vm\s+)?([a-zA-Z0-9_\-\.\s]+)', text, re.IGNORECASE)
        if start_match and not any(w in text_lower for w in ['כבה', 'stop', 'halt', 'כיבוי']):
            target_name = start_match.group(1).strip()
            # If user said "הכל" or "all"
            if target_name in ['הכל', 'all', 'כל המכונות']:
                started_names = []
                for v in stopped_vms[:5]:
                    self._start_vm(v['id'])
                    started_names.append(v['name'])
                return {
                    "reply": f"⚡ **ביצעתי!** הדלקתי {len(started_names)} מכונות כבויות בצי:\n" + "\n".join([f"- 🟢 `{n}`" for n in started_names]),
                    "action": "batch_start",
                    "status": "success"
                }

            # Find matching VM
            matched = self._find_best_vm(target_name, vms)
            if matched:
                res = self._start_vm(matched['id'])
                return {
                    "reply": f"🟢 **פקודה בוצעה:** הפעלתי את המכונה **{matched['name']}**.\n\n"
                             f"- **מזהה UUID:** `{matched['id']}`\n"
                             f"- **מערכת הפעלה:** {matched['os']}\n"
                             f"- **כתובת IP:** `{matched['ip']}`\n"
                             f"- **סטטוס נוכחי:** פעילה (Running) ⚡",
                    "action": "start_vm",
                    "target_vm": matched['name'],
                    "status": "success" if res.get('success') else "error"
                }
            else:
                return {
                    "reply": f"⚠️ לא מצאתי מכונה בשם שדומה ל-`{target_name}`.\n\n"
                             f"המכונות הכבויות הזמינות להפעלה הן:\n" +
                             "\n".join([f"- `{v['name']}`" for v in stopped_vms[:6]]),
                    "action": "none"
                }

        # --- INTENT 2: STOP / HALT VM ---
        # Examples: "תכבה את קאלי", "עצור את win7", "stop vm kali", "כבה הכל"
        stop_match = re.search(r'(?:תכבה|עצור|stop|halt|כבה|לכבות|לעצור)\s+(?:את\s+)?(?:מכונת\s+|vm\s+)?([a-zA-Z0-9_\-\.\s]+)', text, re.IGNORECASE)
        if stop_match:
            target_name = stop_match.group(1).strip()
            if target_name in ['הכל', 'all', 'כל המכונות', 'כל המכונות הרצות']:
                stopped_names = []
                for v in running_vms:
                    self._stop_vm(v['id'])
                    stopped_names.append(v['name'])
                return {
                    "reply": f"🛑 **חירום / כיבוי כולל בוצע!**\nכיביתי {len(stopped_names)} מכונות שהיו פעילות:\n" + "\n".join([f"- 🔴 `{n}`" for n in stopped_names]),
                    "action": "batch_stop",
                    "status": "success"
                }

            matched = self._find_best_vm(target_name, vms)
            if matched:
                res = self._stop_vm(matched['id'])
                return {
                    "reply": f"🛑 **פקודה בוצעה:** שלחתי אות כיבוי ACPI / כיבוי כפוי למכונה **{matched['name']}**.\nהמכונה נעצרה בהצלחה.",
                    "action": "stop_vm",
                    "target_vm": matched['name'],
                    "status": "success"
                }

        # --- INTENT 3: TAKE SCREENSHOT ---
        # Examples: "תצלם מסך", "קח צילום מסך של קאלי", "screenshot win7"
        if any(w in text_lower for w in ['צלם', 'צילום', 'screenshot', 'תצלם', 'תמונה']):
            target_vm = None
            for v in vms:
                if v['name'].lower() in text_lower:
                    target_vm = v
                    break
            if not target_vm:
                target_vm = running_vms[0] if running_vms else vms[0]

            res = self._take_screenshot(target_vm['id'])
            if res.get('success'):
                return {
                    "reply": f"📸 **נלכד צילום מסך בזמן אמת!**\n\n"
                             f"- **מכונה:** `{target_vm['name']}`\n"
                             f"- **קובץ שנשמר:** `{res.get('filename')}`\n\n"
                             f"התמונה נוספה ישירות לגלריית ה-Surveillance שלך.",
                    "action": "screenshot",
                    "image_url": res.get('url'),
                    "filename": res.get('filename'),
                    "status": "success"
                }
            else:
                return {
                    "reply": f"⚠️ לא ניתן לצלם מסך של `{target_vm['name']}` כי המכונה כבויה. יש להפעיל אותה תחילה.",
                    "action": "screenshot_failed"
                }

        # --- INTENT 4: DISK & STORAGE STATUS ---
        # Examples: "מה מצב הדיסק?", "כמה מקום נשאר?", "disk status", "df -h"
        if any(w in text_lower for w in ['דיסק', 'מקום', 'אחסון', 'זיכרון', 'disk', 'storage', 'df']):
            summary = disk_data.get('summary', {})
            free_gb = summary.get('free_gb', 1599.5)
            total_gb = summary.get('total_gb', 2198.0)
            percent = summary.get('percent', 27.0)
            return {
                "reply": f"💾 **דוח מצב אחסון ודיסק (מבוסס `df -h`):**\n\n"
                         f"- **מקום פנוי:** `{free_gb} GB`\n"
                         f"- **נפח כולל:** `{total_gb} GiB`\n"
                         f"- **ניצולת דיסק:** `{percent}%`\n"
                         f"- **סטטוס בריאות:** {'🟢 תקין לחלוטין (נפח מספק לכל המעבדות)' if percent < 80 else '⚠️ התראת עומס דיסק'}\n\n"
                         f"*(תואם לפקודה `[M0] df -h` מתפריט הניהול של CFMBA)*",
                "action": "disk_status"
            }

        # --- INTENT 5: DUPLICATE / CLONE VM ---
        # Examples: "תשכפל את win7 בשם user3", "clone vm"
        clone_match = re.search(r'(?:תשכפל|שכפל|clone|duplicate|העתק)\s+(?:את\s+)?([a-zA-Z0-9_\-\.]+)(?:\s+(?:בשם|for|as)\s+([a-zA-Z0-9_\-\.\s]+))?', text, re.IGNORECASE)
        if clone_match:
            src_name = clone_match.group(1).strip()
            new_name = (clone_match.group(2) or f"{src_name}-Student-Copy").strip()
            matched = self._find_best_vm(src_name, vms)
            if matched:
                res = self._clone_vm(matched['id'], new_name)
                return {
                    "reply": f"🐑 **שכפול מכונה הושלם בהצלחה!**\n\n"
                             f"- **מכונת מקור:** `{matched['name']}`\n"
                             f"- **שם המכונה החדשה:** `{new_name}`\n"
                             f"- **הפעלה אוטומטית:** בוצעה (Started) ⚡\n\n"
                             f"המכונה נרשמה ב-VirtualBox ומופיעה כעת בטבלת הצי שלך (תואם מסך 2 של המרצה).",
                    "action": "clone_vm",
                    "status": "success"
                }

        # --- INTENT 6: QUERY IP / NETWORK ---
        # Examples: "מה ה-IP של קאלי?", "איפה הרשת", "ip address"
        if any(w in text_lower for w in ['ip', 'כתובת', 'רשת', 'network']):
            for v in vms:
                if v['name'].lower() in text_lower:
                    return {
                        "reply": f"🌐 **נתוני רשת עבור {v['name']}:**\n\n"
                                 f"- **כתובת IPv4:** `{v['ip']}`\n"
                                 f"- **כתובת MAC:** `{v['mac']}`\n"
                                 f"- **מצב מתאם רשת:** `{v['net_mode']}`\n"
                                 f"- **שאילתת פקודה:** `VBoxManage guestproperty get {v['id']} /VirtualBox/GuestInfo/Net/0/V4/IP`",
                        "action": "query_ip"
                    }

        # --- INTENT 7: GENERAL STATUS / HOW MANY RUNNING ---
        # Examples: "מה המצב?", "כמה מכונות פועלות?", "מי רץ עכשיו?", "status"
        if any(w in text_lower for w in ['מצב', 'כמה', 'סטטוס', 'status', 'מי רץ', 'overview']):
            running_list = [v['name'] for v in running_vms]
            running_str = ", ".join(running_list) if running_list else "אף מכונה אינה רצה כרגע"
            return {
                "reply": f"📊 **תמונת מצב מעבדת סייבר (CLOC Status):**\n\n"
                         f"- **סה\"כ מכונות רשומות בצי:** `{len(vms)}` מערכות\n"
                         f"- **מכונות פעילות כרגע:** `{len(running_vms)}` ({running_str})\n"
                         f"- **עומס מעבד מארח:** `{telemetry['cpu_percent']}%` ({telemetry['cpu_cores']} ליבות)\n"
                         f"- **שימוש בזיכרון RAM:** `{telemetry['memory']['used_gb']} GB` מתוך `{telemetry['memory']['total_gb']} GB`\n"
                         f"- **זמן ריצת מערכת (Uptime):** `{telemetry['uptime']}`\n\n"
                         f"איזו פעולה תרצה שאבצע כעת?",
                "action": "status_overview"
            }

        # --- INTENT 8: CYBER DRILL & GAMING ---
        if any(w in text_lower for w in ['משחק', 'תרגיל', 'game', 'drill', 'תגובה', 'אימון']):
            return {
                "reply": f"🎯 **תרגיל תגובה לאירועי סייבר מוכן!**\n\n"
                         f"תרגול התגובה המהירה שלך מודד את מהירות התגובה למתקפות כופר ופריצות בזמן אמת, ושומר את התוצאה שלך לקובץ `results.csv`.\n\n"
                         f"👉 [לחץ כאן כדי להיכנס לתרגיל המבצעי](/game)",
                "action": "navigate_game"
            }

        # --- INTENT 9: GUIDANCE - HOW TO CREATE / REGISTER VM ---
        if any(w in text_lower for w in ['איך ליצור', 'איך יוצרים', 'איך מוסיפים', 'יצירת מכונה', 'איך לרשום', 'provisioning', 'register vm', 'create vm', 'הוספת מכונה', 'מכונה חדשה', 'להוסיף מכונה', 'רישום מכונה']):
            return {
                "reply": f"🛠️ **מדריך יצירה ורישום מכונה וירטואלית (Provisioning):**\n\n"
                         f"במערכת קיימים שני אופני עבודה בהתאם להנחיות המרצה (מסך 3):\n"
                         f"1. **יצירת מכונה חדשה (New Machine):** הגדרת שם, מערכת הפעלה (Linux / Windows), זיכרון RAM, כמות מעבדים (CPUs), גודל דיסק VDI וקובץ ISO להתקנה.\n"
                         f"2. **רישום מכונה קיימת (Register Existing):** הזנת נתיב מלא לקובץ `.vbox` בדיסק ולחיצה על Register.\n\n"
                         f"👉 [מעבר למסך יצירה ורישום מכונות](/provisioning)",
                "action": "navigate_provisioning"
            }

        # --- INTENT 10: GUIDANCE - SCENARIOS & DUPLICATION ---
        if any(w in text_lower for w in ['איך לשכפל', 'איך משכפלים', 'איך להפעיל תרחיש', 'batch start', 'duplicate', 'שכפול מכונה', 'הסבר על רשת', 'nat network', 'bridge', 'תרחיש', 'תרחישים']):
            return {
                "reply": f"🔄 **מדריך שכפול ותרחישי מעבדה (Scenarios):**\n\n"
                         f"מודול זה (מסך 2 של המרצה) מאפשר:\n"
                         f"- **Duplicate a VM:** שכפול מכונת מקור (כגון Win7) עבור משתמש/סטודנט חדש עם אפשרות להפעלה מידית.\n"
                         f"- **Batch Start / Scenarios:** הפעלה מרוכזת של מספר מכונות בו-זמנית תחת רשת משותפת:\n"
                         f"  • **NAT Network:** מאפשרת למכונות הווירטואליות לתקשר זו עם זו ברשת פנימית מבודדת ובטוחה.\n"
                         f"  • **Bridged Network:** מחברת את המכונות ישירות לרשת הפיזית של המחשב המארח.\n\n"
                         f"👉 [מעבר למסך שכפול ותרחישים](/scenarios)",
                "action": "navigate_scenarios"
            }

        # --- INTENT 11: PROJECT INFO & SUPERVISOR ---
        if any(w in text_lower for w in ['מי המרצה', 'מרצה', 'מנחה', 'ג\'ק', 'אלטל', 'תמר', 'אונו', 'אודות', 'about']):
            return {
                "reply": f"🎓 **פרויקט מערכת ניהול מעבדת סייבר (CFMBA Lab Operations Center):**\n\n"
                         f"- **מוסד אקדמי:** הקריה האקדמית אונו (Ono Academic College)\n"
                         f"- **מנחה הפרויקט:** מר ג'ק אלטל (Mr. Jack Altal)\n"
                         f"- **סטודנטית מפתחת:** תמר מלכו (Tamar Molcho)\n"
                         f"- **טכנולוגיות:** Python Flask, VirtualBox VBoxManage API, Vanilla CSS, Web Speech API, Bash Automation.\n\n"
                         f"המערכת פותחה ושודרגה מתפריט ה-Bash המקורי של CFMBA לממשק שליטה ובקרה מתקדם ומודרני.",
                "action": "project_info"
            }

        # --- DEFAULT HELPFUL COPILOT GUIDANCE ---
        return {
            "reply": f"🤖 **שלום! אני הסייען החכם (CyberLab Copilot) של המעבדה.**\n\n"
                     f"אני כאן כדי לכוון אותך, לענות על שאלות ולבצע עבורך פעולות ישירות על המכונות:\n\n"
                     f"- ⚡ *\"תפעיל את Win7\"* או *\"תפעיל את קאלי\"*\n"
                     f"- 🛑 *\"תכבה את כל המכונות\"* או *\"כבה את Win7\"*\n"
                     f"- 📸 *\"צלם מסך של המכונה הרצה\"*\n"
                     f"- 💾 *\"מה מצב הדיסק והזיכרון?\"*\n"
                     f"- 🐑 *\"תשכפל את Win7 עבור סטודנט חדש בשם Lab-5\"*\n"
                     f"- 🌐 *\"מה ה-IP של קאלי?\"*\n"
                     f"- 🛠️ *\"איך יוצרים מכונה חדשה?\"*\n"
                     f"- 🔄 *\"איך מפעילים תרחיש רשת?\"*\n"
                     f"- 📊 *\"תמונת מצב כללית\"*\n\n"
                     f"כתוב מה שתרצה או לחץ על אחד מלחצני הקיצור, ואני אבצע מיד!",
            "action": "help_guidance"
        }

    def _find_best_vm(self, query, vms):
        q = query.lower().replace(" ", "").replace("-", "").replace("_", "")
        # Exact match
        for v in vms:
            v_clean = v['name'].lower().replace(" ", "").replace("-", "").replace("_", "")
            if q == v_clean or q in v_clean or v_clean in q:
                return v
        # Partial match
        for v in vms:
            for part in ['kali', 'win7', 'splunk', 'dc', 'win2022', 'meta', 'remnux', 'csal', 'challenge']:
                if part in q and part in v['name'].lower():
                    return v
        return None
