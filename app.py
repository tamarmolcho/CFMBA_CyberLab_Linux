import os
import csv
import time
import json
import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from vbox_manager import VBoxManager
from system_service import SystemService
from agent_service import LabAgent

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
RESULTS_CSV = os.path.join(BASE_DIR, "results.csv")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
SECRET_KEY_FILE = os.path.join(BASE_DIR, ".secret_key")

def get_or_create_secret_key():
    """Generates and persists a cryptographically secure secret key"""
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    if os.path.exists(SECRET_KEY_FILE):
        try:
            with open(SECRET_KEY_FILE, "r") as f:
                k = f.read().strip()
                if len(k) >= 32:
                    return k
        except Exception:
            pass
    new_key = os.urandom(32).hex()
    try:
        with open(SECRET_KEY_FILE, "w") as f:
            f.write(new_key)
        os.chmod(SECRET_KEY_FILE, 0o600)
    except Exception:
        pass
    return new_key

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
app.secret_key = get_or_create_secret_key()
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024 * 5  # 5GB for OVA files
app.config['UPLOAD_FOLDER'] = UPLOADS_DIR

vbox_mgr = VBoxManager(STATIC_DIR, demo_enabled=True)
sys_service = SystemService()
lab_agent = LabAgent(vbox_mgr, sys_service)

# Available laboratory modules for granular RBAC assignment
ALL_MODULES = [
    {"id": "dashboard", "name": "VM Dashboard", "icon": "📊"},
    {"id": "scenarios", "name": "Duplicate & Scenarios", "icon": "🔄"},
    {"id": "provisioning", "name": "Create / Register VM", "icon": "➕"},
    {"id": "disk", "name": "Disk Status (df -h)", "icon": "💾"},
    {"id": "surveillance", "name": "Surveillance & Screen", "icon": "📸"},
    {"id": "network", "name": "Network & IP Recon", "icon": "🌐"},
    {"id": "terminal", "name": "Cyber Console", "icon": "⌨️"},
    {"id": "game", "name": "Threat Drill Test", "icon": "🎯"},
    {"id": "copilot", "name": "CyberCopilot AI", "icon": "🤖"},
]
ALL_MODULE_IDS = [m["id"] for m in ALL_MODULES]

MODULE_ROUTES = {
    "dashboard": "index",
    "scenarios": "scenarios_page",
    "provisioning": "import_page",
    "disk": "disk_page",
    "surveillance": "surveillance_page",
    "network": "network_page",
    "terminal": "console_page",
    "game": "game",
    "copilot": "index"
}

# Default seed users with pre-hashed credentials
DEFAULT_USERS = {
    "admin": {
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "full_name": "Tamar Molcho",
        "role": "admin",
        "role_badge": "Admin",
        "email": "tamar.molcho@ono.ac.il",
        "college": "Ono Academic College",
        "supervisor": "Mr. Jack Altal",
        "permissions": ALL_MODULE_IDS,
        "created_by": "system",
        "created_at": "2026-09-01",
        "last_login": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    "jack": {
        "username": "jack",
        "password": generate_password_hash("jack123"),
        "full_name": "Mr. Jack Altal",
        "role": "lecturer",
        "role_badge": "Supervisor",
        "email": "jack.altal@ono.ac.il",
        "college": "Ono Academic College",
        "supervisor": "Ono Cyber Department",
        "permissions": ALL_MODULE_IDS,
        "created_by": "admin",
        "created_at": "2026-08-15",
        "last_login": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    "lecturer": {
        "username": "lecturer",
        "password": generate_password_hash("lecturer123"),
        "full_name": "Mr. Jack Altal",
        "role": "lecturer",
        "role_badge": "Supervisor",
        "email": "jack.altal@ono.ac.il",
        "college": "Ono Academic College",
        "supervisor": "Ono Cyber Department",
        "permissions": ALL_MODULE_IDS,
        "created_by": "admin",
        "created_at": "2026-08-15",
        "last_login": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    "student": {
        "username": "student",
        "password": generate_password_hash("student123"),
        "full_name": "Cyber Lab Student",
        "role": "student",
        "role_badge": "Student",
        "email": "student@ono.ac.il",
        "college": "Ono Academic College",
        "supervisor": "Mr. Jack Altal",
        "permissions": [],  # Zero permissions until granted by Lecturer or Admin
        "created_by": "jack",
        "created_at": "2026-10-01",
        "last_login": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    "dan": {
        "username": "dan",
        "password": generate_password_hash("dan123"),
        "full_name": "Dan Cohen",
        "role": "student",
        "role_badge": "Student",
        "email": "dan.cohen@ono.ac.il",
        "college": "Ono Academic College",
        "supervisor": "Mr. Jack Altal",
        "permissions": ["game", "surveillance"],  # Selective permission grant demo
        "created_by": "jack",
        "created_at": "2026-10-02",
        "last_login": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
}

def load_users():
    """Loads users and ensures all passwords are securely hashed with Werkzeug"""
    users = {}
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
    if not users:
        users = DEFAULT_USERS.copy()

    # Automatically upgrade any plaintext passwords to secure cryptographic hashes
    needs_save = False
    for uname, u in users.items():
        pwd = u.get("password")
        if pwd and not (pwd.startswith("scrypt:") or pwd.startswith("pbkdf2:")):
            u["password"] = generate_password_hash(pwd)
            needs_save = True
        # Admin always maintains full permissions
        if uname == "admin":
            u["permissions"] = ALL_MODULE_IDS

    if needs_save or not os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving user hashes: {e}")
    return users

def save_users():
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(USERS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving users: {e}")

USERS = load_users()

def get_current_user():
    username = session.get('username')
    if username and username in USERS:
        return USERS[username]
    return None

def is_safe_url(target):
    """Prevents open redirect vulnerabilities"""
    if not target or not isinstance(target, str):
        return False
    return target.startswith('/') and not target.startswith('//') and '\\' not in target

def has_permission(user, module_id):
    if not user:
        return False
    # Admin has access to change and view everything, always
    if user.get('role') == 'admin':
        return True
    return module_id in user.get('permissions', [])

@app.context_processor
def inject_user():
    curr = get_current_user() or {
        "username": "guest", "full_name": "Guest Operator", "role": "guest", "role_badge": "Guest", "permissions": []
    }
    return {
        'current_user': curr,
        'has_permission': lambda m: has_permission(curr, m),
        'can_access': lambda m: has_permission(curr, m),
        'all_modules': ALL_MODULES
    }

def require_permission(module_id):
    """Enforces module permissions for both web views and JSON API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"success": False, "error": "Authentication required"}), 401
                return redirect(url_for('login', next=request.path))
            if not has_permission(user, module_id):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"success": False, "error": f"Permission denied for module '{module_id}'"}), 403
                flash(f"שגיאת הרשאה: אין לך גישה למודול '{module_id}'. פנה למרצה או לאדמין.", "error")
                return render_template('access_denied.html', module=module_id, user=user), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(*allowed_roles):
    """Enforces specific user roles (e.g. admin or lecturer)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"success": False, "error": "Authentication required"}), 401
                return redirect(url_for('login', next=request.path))
            if user.get('role') not in allowed_roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"success": False, "error": "Role unauthorized"}), 403
                flash("גישה מוגבלת: אין לך הרשאת תפקיד לבצע פעולה זו.", "error")
                return render_template('access_denied.html', module="Role Authorization", user=user), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.before_request
def require_login():
    allowed_paths = ['/login', '/logout']
    if request.path.startswith('/static') or request.path in allowed_paths:
        return None
    user = get_current_user()
    if not user:
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({"success": False, "error": "Authentication required"}), 401
        return redirect(url_for('login', next=request.path))

# In-memory audit log of cyber operations
AUDIT_LOGS = [
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "source": "SYSTEM", "event": "CFMBA CyberLab Operations Core initialized.", "level": "info"},
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "source": "VBOX", "event": "VirtualBox Engine interface synchronized.", "level": "success"},
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "source": "NETWORK", "event": "Host-Only Cyber Subnet [192.168.56.0/24] detected.", "level": "info"},
]

def log_event(source, event, level="info"):
    AUDIT_LOGS.insert(0, {
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "source": source,
        "event": event,
        "level": level
    })
    if len(AUDIT_LOGS) > 50:
        AUDIT_LOGS.pop()

# --- PAGES ---

@app.route('/')
def index():
    """Mission Control / Operations Dashboard"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # If student or lecturer doesn't have dashboard permission:
    if not has_permission(user, 'dashboard'):
        # Redirect to their first available allowed module
        for p in user.get('permissions', []):
            if p in MODULE_ROUTES and p != 'dashboard':
                return redirect(url_for(MODULE_ROUTES[p]))
        return render_template('access_denied.html', module="VM Dashboard", user=user)

    vms = vbox_mgr.get_all_vms()
    running_count = sum(1 for v in vms if v["state"] == "running")
    stopped_count = sum(1 for v in vms if v["state"] == "stopped")
    telemetry = sys_service.get_system_telemetry()
    disk_data = sys_service.get_df_h()
    return render_template(
        'index.html',
        vms=vms,
        running_count=running_count,
        stopped_count=stopped_count,
        total_vms=len(vms),
        telemetry=telemetry,
        disk_data=disk_data,
        logs=AUDIT_LOGS[:12]
    )

@app.route('/vms')
@require_permission('dashboard')
def vms_page():
    """Virtual Machines Fleet Manager"""
    vms = vbox_mgr.get_all_vms()
    return render_template('vms.html', vms=vms)

@app.route('/network')
@require_permission('network')
def network_page():
    """Network & IP Reconnaissance Inspector"""
    vms = vbox_mgr.get_all_vms()
    return render_template('network.html', vms=vms)

@app.route('/surveillance')
@require_permission('surveillance')
def surveillance_page():
    """Live VM Screenshots & Visual Reconnaissance"""
    vms = vbox_mgr.get_all_vms()
    screens_dir = os.path.join(STATIC_DIR, "screenshots")
    screenshots = []
    if os.path.exists(screens_dir):
        files = sorted(os.listdir(screens_dir), key=lambda x: os.path.getmtime(os.path.join(screens_dir, x)), reverse=True)
        for f in files:
            if f.endswith(('.png', '.jpg', '.webp')):
                fpath = os.path.join(screens_dir, f)
                screenshots.append({
                    "filename": f,
                    "url": f"/static/screenshots/{f}",
                    "size_kb": round(os.path.getsize(fpath) / 1024, 1),
                    "created": datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S")
                })
    return render_template('surveillance.html', vms=vms, screenshots=screenshots)

@app.route('/scenarios')
@app.route('/environments')
@require_permission('scenarios')
def scenarios_page():
    """Matches Screenshot 2: Duplicate a VM & Scenarios (Batch Start)"""
    vms = vbox_mgr.get_all_vms()
    stopped = [v for v in vms if v['state'] != 'running']
    return render_template('scenarios.html', vms=vms, stopped=stopped)

@app.route('/provisioning')
@app.route('/import')
@require_permission('provisioning')
def import_page():
    """Matches Screenshot 3: Create or register a VM & Extension packs"""
    uploaded_files = []
    if os.path.exists(UPLOADS_DIR):
        for f in os.listdir(UPLOADS_DIR):
            if f.endswith(('.ova', '.ovf')):
                fpath = os.path.join(UPLOADS_DIR, f)
                uploaded_files.append({
                    "name": f,
                    "path": fpath,
                    "size_mb": round(os.path.getsize(fpath) / (1024**2), 1)
                })
    extpacks = vbox_mgr.get_extpacks()
    return render_template('import.html', uploads=uploaded_files, extpacks=extpacks)

@app.route('/disk')
@require_permission('disk')
def disk_page():
    """Storage & df -h Telemetry"""
    df_result = sys_service.get_df_h()
    return render_template('disk.html', df_result=df_result)

@app.route('/terminal')
@app.route('/ops-console')
@require_permission('terminal')
def console_page():
    """Interactive Cyber Operations Terminal"""
    return render_template('console.html')

@app.route('/game')
@require_permission('game')
def game():
    """Cyber Threat Incident Response Drill (Reaction Time Test)"""
    leaderboard = get_leaderboard_data()
    return render_template('game.html', leaderboard=leaderboard, results=leaderboard)

@app.route('/erd')
def erd_page():
    """Entity Relationship Diagram (ERD) Viewer"""
    return render_template('erd.html')

# --- USER MANAGEMENT & RBAC PERMISSIONS ---

@app.route('/users')
@require_role('admin', 'lecturer')
def users_page():
    """User Management and Granular RBAC Permissions"""
    return render_template('users.html', users=USERS, all_modules=ALL_MODULES)

@app.route('/users/create', methods=['POST'])
@require_role('admin', 'lecturer')
def user_create():
    """Create user with role constraints: Lecturer can ONLY add students"""
    curr = get_current_user()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    requested_role = request.form.get('role', 'student').strip()
    selected_perms = request.form.getlist('permissions')

    # Security rule: Lecturer can ONLY create students!
    if curr.get('role') == 'lecturer' and requested_role != 'student':
        flash("שגיאת אבטחה: למרצה מותר להוסיף סטודנטים בלבד!", "error")
        return redirect(url_for('users_page'))

    if not username or not password or not full_name:
        flash("נא למלא את כל שדות החובה.", "error")
        return redirect(url_for('users_page'))

    if username in USERS:
        flash(f"שם המשתמש '{username}' כבר קיים במערכת.", "error")
        return redirect(url_for('users_page'))

    role_badge = "Admin" if requested_role == 'admin' else ("Supervisor" if requested_role == 'lecturer' else "Student")

    if requested_role == 'admin':
        permissions = ALL_MODULE_IDS
    else:
        permissions = [p for p in selected_perms if p in ALL_MODULE_IDS]

    USERS[username] = {
        "username": username,
        "password": generate_password_hash(password),
        "full_name": full_name,
        "role": requested_role,
        "role_badge": role_badge,
        "email": email or f"{username}@ono.ac.il",
        "college": "Ono Academic College",
        "supervisor": curr.get('full_name'),
        "permissions": permissions,
        "created_by": curr.get('username'),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
        "last_login": "Never"
    }
    save_users()
    log_event("RBAC", f"User '{username}' ({requested_role}) created by '{curr['username']}'.", "success")
    flash(f"המשתמש {full_name} (@{username}) נוצר בהצלחה עם הרשאות מוגדרות!", "success")
    return redirect(url_for('users_page'))

@app.route('/users/delete/<username>', methods=['POST'])
@require_role('admin', 'lecturer')
def user_delete(username):
    """Delete user: Admin can delete any except self; Lecturer can only delete students"""
    curr = get_current_user()
    if username == curr.get('username'):
        flash("לא ניתן למחוק את החשבון המחובר הנוכחי.", "error")
        return redirect(url_for('users_page'))

    if username == 'admin':
        flash("לא ניתן למחוק את מנהלת המערכת הראשית.", "error")
        return redirect(url_for('users_page'))

    target = USERS.get(username)
    if not target:
        flash("משתמש לא נמצא.", "error")
        return redirect(url_for('users_page'))

    # Security rule: Lecturer can ONLY delete students!
    if curr.get('role') == 'lecturer' and target.get('role') != 'student':
        flash("שגיאת אבטחה: למרצה מותר למחוק סטודנטים בלבד!", "error")
        return redirect(url_for('users_page'))

    del USERS[username]
    save_users()
    log_event("RBAC", f"User '{username}' deleted by '{curr['username']}'.", "info")
    flash(f"המשתמש @{username} נמחק מהמערכת בהצלחה.", "info")
    return redirect(url_for('users_page'))

@app.route('/users/permissions', methods=['POST'])
@require_role('admin', 'lecturer')
def user_update_permissions():
    """Update permissions: Admin can update anyone; Lecturer can only update students"""
    curr = get_current_user()
    username = request.form.get('username', '').strip()
    target = USERS.get(username)
    if not target:
        flash("משתמש לא נמצא.", "error")
        return redirect(url_for('users_page'))

    # Security rule: Lecturer can ONLY update student permissions!
    if curr.get('role') == 'lecturer' and target.get('role') != 'student':
        flash("שגיאת אבטחה: למרצה מותר לעדכן הרשאות לסטודנטים בלבד!", "error")
        return redirect(url_for('users_page'))

    selected_perms = request.form.getlist('permissions')
    target['permissions'] = [p for p in selected_perms if p in ALL_MODULE_IDS]
    save_users()
    log_event("RBAC", f"Permissions updated for user '{username}' by '{curr['username']}'.", "success")
    flash(f"הרשאות המשתמש {target['full_name']} עודכנו בהצלחה!", "success")
    return redirect(url_for('users_page'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authentication Login Page with Password Hash Verification"""
    if request.method == 'POST':
        uname = request.form.get('username', '').strip().lower()
        pwd = request.form.get('password', '').strip()
        user = USERS.get(uname)
        if user and check_password_hash(user['password'], pwd):
            session['username'] = uname
            user['last_login'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_users()
            log_event("AUTH", f"User '{uname}' logged in successfully.", "success")
            flash(f"ברוך הבא, {user['full_name']}! התחברת בהצלחה למרכז השליטה.", "success")
            next_url = request.args.get('next')
            if not is_safe_url(next_url):
                next_url = None
            # If student without dashboard permission logs in, redirect to first allowed module or profile
            if user['role'] == 'student' and 'dashboard' not in user.get('permissions', []):
                for m in user.get('permissions', []):
                    if m in MODULE_ROUTES and m != 'dashboard':
                        return redirect(url_for(MODULE_ROUTES[m]))
                return redirect(url_for('profile_page'))
            return redirect(next_url or url_for('index'))
        else:
            flash("שם משתמש או סיסמה שגויים. נא לנסות שוב.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Sign out and terminate user session"""
    uname = session.get('username', 'operator')
    session.clear()
    log_event("AUTH", f"User '{uname}' signed out.", "info")
    flash("התנתקת בהצלחה ממרכז השליטה של CFMBA.", "info")
    return redirect(url_for('login'))

@app.route('/profile')
@app.route('/user/<username>')
def profile_page(username=None):
    """User Profile with privacy access controls"""
    curr = get_current_user() or USERS['admin']
    if username and username in USERS:
        if curr.get('role') == 'admin' or username == curr.get('username'):
            user = USERS[username]
        else:
            flash("אינך מורשה לצפות בפרופיל של משתמשים אחרים.", "error")
            return redirect(url_for('profile_page'))
    else:
        user = curr
    return render_template('profile.html', user=user, users=USERS)

@app.route('/api/profile/update', methods=['POST'])
def api_profile_update():
    """Update user profile information with persistent save"""
    curr = get_current_user()
    if not curr:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    uname = curr['username']
    data = request.json or request.form
    if 'full_name' in data and data['full_name'].strip():
        USERS[uname]['full_name'] = data['full_name'].strip()
    if 'email' in data and data['email'].strip():
        USERS[uname]['email'] = data['email'].strip()
    save_users()
    log_event("PROFILE", f"User '{uname}' profile updated.", "info")
    return jsonify({"success": True, "message": "הפרופיל עודכן בהצלחה", "user": USERS[uname]})

# --- USER'S EXACT CSV ROUTE & LOGIC ---

@app.route('/save_result', methods=['POST'])
def save_result():
    """Preserves user's exact reaction time saving logic with results.csv"""
    data = request.json or {}
    try:
        reaction_time = float(data.get('reactionTime', 0))
    except (ValueError, TypeError):
        reaction_time = 0.0
    full_name = str(data.get('fullName', 'Anonymous Operator')).strip() or 'Anonymous Operator'

    with open(RESULTS_CSV, 'a', newline='') as csvfile:
        fieldnames = ['fullName', 'reactionTime']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        writer.writerow({'fullName': full_name, 'reactionTime': reaction_time})

    log_event("DRILL", f"Operator '{full_name}' logged reaction score: {reaction_time}ms", "success")
    return jsonify({
        'message': 'Result saved successfully!',
        'fullName': full_name,
        'reactionTime': reaction_time,
        'leaderboard': get_leaderboard_data()
    })

def get_leaderboard_data():
    results = []
    if os.path.exists(RESULTS_CSV):
        try:
            with open(RESULTS_CSV, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'reactionTime' in row and 'fullName' in row:
                        try:
                            results.append({
                                'fullName': row['fullName'],
                                'reactionTime': float(row['reactionTime'])
                            })
                        except ValueError:
                            pass
        except Exception:
            pass
    results.sort(key=lambda x: x['reactionTime'])
    return results[:10]

# --- API ENDPOINTS (PROTECTED WITH RBAC) ---

@app.route('/api/telemetry')
def api_telemetry():
    vms = vbox_mgr.get_all_vms()
    running_count = sum(1 for v in vms if v["state"] == "running")
    sys_metrics = sys_service.get_system_telemetry()
    disk = sys_service.get_df_h()
    return jsonify({
        "telemetry": sys_metrics,
        "vms": {
            "total": len(vms),
            "running": running_count,
            "stopped": len(vms) - running_count
        },
        "disk": disk["summary"],
        "logs": AUDIT_LOGS[:8]
    })

@app.route('/api/vms')
@require_permission('dashboard')
def api_vms():
    return jsonify(vbox_mgr.get_all_vms())

@app.route('/api/vm/<vmid>/action', methods=['POST'])
@app.route('/api/vm/<vmid>/<action_name>', methods=['POST'])
@require_permission('dashboard')
def api_vm_action(vmid, action_name=None):
    if action_name:
        action = action_name
    else:
        action = request.json.get('action') if request.json else request.form.get('action')
    if action == 'start':
        res = vbox_mgr.start_vm(vmid)
        log_event("VM_CONTROL", f"VM '{vmid}' boot initiated: {res['message']}", "success" if res["success"] else "error")
        return jsonify(res)
    elif action == 'stop':
        force = bool(request.json.get('force', False)) if request.json else False
        res = vbox_mgr.stop_vm(vmid, force=force)
        log_event("VM_CONTROL", f"VM '{vmid}' halt command executed: {res['message']}", "warning" if res["success"] else "error")
        return jsonify(res)
    elif action == 'pause':
        res = vbox_mgr.pause_vm(vmid)
        log_event("VM_CONTROL", f"VM '{vmid}' toggle pause: {res['message']}", "info")
        return jsonify(res)
    elif action == 'screenshot':
        res = vbox_mgr.take_screenshot(vmid)
        log_event("SURVEILLANCE", f"Live screenshot captured for '{vmid}'", "info" if res["success"] else "error")
        return jsonify(res)
    else:
        return jsonify({"success": False, "message": f"Unknown action: {action}"}), 400

@app.route('/api/vm/<vmid>/ip')
@require_permission('network')
def api_vm_ip(vmid):
    """Executes: VBoxManage guestproperty get $vmid "/VirtualBox/GuestInfo/Net/0/V4/IP" """
    vm = vbox_mgr.get_vm_by_id(vmid)
    if not vm:
        return jsonify({"success": False, "error": "VM not found"}), 404
    
    if vm.get("is_simulated"):
        ip = vm.get("ip", "192.168.56.10")
    else:
        ip = vbox_mgr.get_real_vm_ip(vmid)
    
    return jsonify({
        "success": True,
        "vmid": vmid,
        "name": vm.get("name"),
        "ip": ip,
        "property": "/VirtualBox/GuestInfo/Net/0/V4/IP"
    })

@app.route('/api/probe', methods=['POST'])
@require_permission('network')
def api_probe():
    data = request.json or {}
    ip = data.get('ip')
    port = data.get('port')
    if not ip:
        return jsonify({"success": False, "message": "IP address required"}), 400
    res = sys_service.test_connectivity(ip, port)
    return jsonify(res)

@app.route('/api/execute', methods=['POST'])
@require_permission('terminal')
def api_execute():
    cmd = request.json.get('command', '') if request.json else ''
    res = sys_service.execute_terminal_cmd(cmd)
    log_event("TERMINAL", f"Executed: {cmd[:40]}... [{ 'OK' if res['success'] else 'FAIL' }]", "info" if res["success"] else "warning")
    return jsonify(res)

@app.route('/api/vm/duplicate', methods=['POST'])
@require_permission('scenarios')
def api_vm_duplicate():
    data = request.json or request.form
    source_id = data.get('source_id')
    new_name = data.get('new_name')
    copy_state = data.get('copy_state', 'current')
    start_after = bool(data.get('start_after'))
    res = vbox_mgr.clone_vm(source_id, new_name, copy_state, start_after)
    log_event("PROVISIONING", f"Duplicate VM '{new_name}' from '{source_id}': {res['message']}", "success" if res["success"] else "error")
    return jsonify(res)

@app.route('/api/scenario/launch', methods=['POST'])
@require_permission('scenarios')
def api_scenario_launch():
    data = request.json or request.form
    scenario_name = data.get('scenario_name', 'Lab Scenario')
    network_mode = data.get('network_mode', 'NAT Network')
    selected_vms = data.get('vms', [])
    if isinstance(selected_vms, str):
        selected_vms = [selected_vms]
    res = vbox_mgr.launch_scenario(scenario_name, network_mode, selected_vms)
    log_event("SCENARIO", f"Batch Start Scenario '{scenario_name}': {res['message']}", "success")
    return jsonify(res)

@app.route('/api/vm/create', methods=['POST'])
@require_permission('provisioning')
def api_vm_create():
    data = request.json or request.form
    name = data.get('name')
    ostype = data.get('ostype', 'Debian_64')
    memory_mb = data.get('memory_mb', 4096)
    cpus = data.get('cpus', 2)
    vdi_mb = data.get('vdi_mb', 81920)
    iso = data.get('iso')
    res = vbox_mgr.create_vm(name, ostype, memory_mb, cpus, vdi_mb, iso)
    log_event("PROVISIONING", f"Created VM '{name}': {res['message']}", "success" if res["success"] else "error")
    return jsonify(res)

@app.route('/api/vm/register', methods=['POST'])
@require_permission('provisioning')
def api_vm_register():
    data = request.json or request.form
    vbox_path = data.get('vbox_path')
    res = vbox_mgr.register_vm(vbox_path)
    log_event("PROVISIONING", f"Register VM '{vbox_path}': {res['message']}", "success" if res["success"] else "error")
    return jsonify(res)

@app.route('/api/upload_ova', methods=['POST'])
@require_permission('provisioning')
def api_upload_ova():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    clean_name = secure_filename(file.filename)
    if clean_name and (clean_name.endswith('.ova') or clean_name.endswith('.ovf')):
        dest = os.path.join(UPLOADS_DIR, clean_name)
        file.save(dest)
        log_event("STORAGE", f"OVA Appliance uploaded: {clean_name}", "success")
        return jsonify({"success": True, "message": f"File '{clean_name}' uploaded.", "filename": clean_name, "path": dest})
    return jsonify({"success": False, "message": "Only .ova or .ovf files allowed"}), 400

@app.route('/api/import_ova', methods=['POST'])
@require_permission('provisioning')
def api_import_ova():
    """Secure OVA appliance import: prevents path traversal and validates file existence"""
    data = request.json or {}
    filename = data.get('filename', '')
    vmname = data.get('vmname')
    cpus = data.get('cpus')
    ram = data.get('ram')
    
    if not filename:
        return jsonify({"success": False, "message": "Filename required"}), 400
    
    # Path traversal protection: only allow legitimate files located in uploads directory
    clean_name = secure_filename(os.path.basename(filename))
    if not clean_name or not (clean_name.endswith('.ova') or clean_name.endswith('.ovf')):
        return jsonify({"success": False, "message": "Invalid OVA file format"}), 400
        
    path = os.path.join(UPLOADS_DIR, clean_name)
    if not os.path.exists(path):
        return jsonify({"success": False, "message": f"Appliance file '{clean_name}' not found in uploads directory"}), 404
        
    res = vbox_mgr.import_ova(path, vm_name=vmname, cpus=cpus, ram=ram)
    log_event("DEPLOYMENT", f"Appliance import '{vmname or clean_name}': {res['message']}", "success" if res["success"] else "error")
    return jsonify(res)

@app.route('/api/toggle_demo', methods=['POST'])
@require_permission('dashboard')
def api_toggle_demo():
    vbox_mgr.demo_enabled = not vbox_mgr.demo_enabled
    vbox_mgr.invalidate_vm_cache()
    mode = "Enabled" if vbox_mgr.demo_enabled else "Disabled"
    log_event("SYSTEM", f"Cyber Range Simulation Mode {mode}.", "info")
    return jsonify({"success": True, "demo_enabled": vbox_mgr.demo_enabled})

@app.route('/api/agent/chat', methods=['POST'])
@require_permission('copilot')
def api_agent_chat():
    data = request.json or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"reply": "נא להזין הודעה או פקודה לסייען המעבדה."}), 400
    res = lab_agent.process_message(message)
    log_event("AI_AGENT", f"Copilot action: '{res.get('action')}' (input: '{message[:30]}')", "info")
    return jsonify(res)

if __name__ == '__main__':
    if not os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['fullName', 'reactionTime'])
            writer.writeheader()
            writer.writerow({'fullName': 'Shadow_Operative_01', 'reactionTime': 248.5})
            writer.writerow({'fullName': 'Ghost_Analyst_Red', 'reactionTime': 282.1})
            writer.writerow({'fullName': 'CyberSentinel_Blue', 'reactionTime': 315.0})
    port = int(os.environ.get('PORT', 5050))
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    print(f"[*] CFMBA CyberLab Operations Center launching on http://127.0.0.1:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
