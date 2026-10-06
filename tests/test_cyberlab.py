import pytest
import os
import json
from app import app, USERS, is_safe_url, has_permission
from system_service import SystemService

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

def test_password_hashing():
    """Verify that stored passwords are cryptographically hashed and never plaintext"""
    for uname, user in USERS.items():
        pwd = user['password']
        assert pwd.startswith(('scrypt:', 'pbkdf2:')), f"User {uname} has unhashed plaintext password!"

def test_login_success_and_failure(client):
    """Test login authentication logic"""
    # Bad credentials
    resp = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'})
    assert resp.status_code == 200
    assert b"login-username" in resp.data

    # Valid credentials
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    assert resp.status_code == 302
    assert resp.headers['Location'] == '/'

def test_unauthenticated_redirect(client):
    """Unauthenticated users must be redirected to /login"""
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

def test_student_permission_restrictions(client):
    """Student with 0 permissions must be blocked from sensitive endpoints"""
    # Login as student
    client.post('/login', data={'username': 'student', 'password': 'student123'})

    # Web page access blocked with 403
    resp = client.get('/terminal')
    assert resp.status_code == 403
    assert b"Access Restricted" in resp.data

    # API execution blocked with 403 JSON
    resp = client.post('/api/execute', json={'command': 'uptime'})
    assert resp.status_code == 403
    data = json.loads(resp.data)
    assert data.get('success') is False
    assert "Permission denied" in data.get('error', '')

    # User management blocked with 403
    resp = client.get('/users')
    assert resp.status_code == 403

def test_command_injection_prevention():
    """Terminal command execution must strictly prevent chaining and unauthorized access"""
    sys_srv = SystemService()

    # Chaining with semicolon
    res = sys_srv.execute_terminal_cmd("ls; whoami")
    assert res['success'] is False
    assert "Shell metacharacter" in res['output']

    # Chaining with pipe
    res = sys_srv.execute_terminal_cmd("ls | grep txt")
    assert res['success'] is False
    assert "Shell metacharacter" in res['output']

    # Chaining with background &
    res = sys_srv.execute_terminal_cmd("uptime & whoami")
    assert res['success'] is False
    assert "Shell metacharacter" in res['output']

    # Reading credentials via cat (cat is forbidden)
    res = sys_srv.execute_terminal_cmd("cat users.json")
    assert res['success'] is False
    assert "is not permitted" in res['output'] or "restricted" in res['output']

    # Whitelisted command without metacharacters must succeed
    res = sys_srv.execute_terminal_cmd("uptime")
    assert res['success'] is True

def test_path_traversal_ova_import(client):
    """Importing appliance with path traversal must be rejected"""
    # Login as admin
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})

    # Path traversal attempt
    resp = client.post('/api/import_ova', json={'filename': '../../etc/shadow'})
    assert resp.status_code in [400, 404]

def test_lecturer_role_constraints(client):
    """Lecturer must NOT be allowed to create an admin or lecturer account"""
    # Login as lecturer
    client.post('/login', data={'username': 'jack', 'password': 'jack123'})

    # Attempt to create an admin
    resp = client.post('/users/create', data={
        'username': 'fakeadmin',
        'password': 'password123',
        'full_name': 'Fake Admin',
        'email': 'fake@ono.ac.il',
        'role': 'admin'
    })
    assert resp.status_code == 302
    assert 'fakeadmin' not in USERS

def test_safe_open_redirect():
    """Open redirect URLs must be rejected"""
    assert is_safe_url('/dashboard') is True
    assert is_safe_url('/profile') is True
    assert is_safe_url('https://evil.com') is False
    assert is_safe_url('//evil.com') is False
    assert is_safe_url('/\\evil.com') is False
    assert is_safe_url('') is False
    assert is_safe_url(None) is False

def test_all_admin_routes_render_ok(client):
    """Admin must have full access to all dashboard routes without template or render errors"""
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    routes = [
        '/',
        '/vms',
        '/scenarios',
        '/surveillance',
        '/network',
        '/import',
        '/disk',
        '/terminal',
        '/game',
        '/profile',
        '/users'
    ]
    for route in routes:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"

def test_api_telemetry_and_vms(client):
    """Telemetry and VM fleet APIs must return structured, non-empty JSON"""
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    
    # Telemetry
    resp = client.get('/api/telemetry')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'telemetry' in data
    assert 'cpu_percent' in data['telemetry']
    assert 'vms' in data
    assert 'running' in data['vms']
    assert 'total' in data['vms']

    # VM Fleet
    resp = client.get('/api/vms')
    assert resp.status_code == 200
    vms_data = json.loads(resp.data)
    assert isinstance(vms_data, list)
    assert len(vms_data) > 0
    assert 'name' in vms_data[0]

def test_api_demo_toggle(client):
    """Simulation mode toggle must switch states and return success"""
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    resp = client.post('/api/toggle_demo')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get('success') is True
    assert 'demo_enabled' in data

def test_ai_agent_chat(client):
    """AI Agent Copilot endpoint must respond with intelligent guidance"""
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    resp = client.post('/api/agent/chat', json={'message': 'status'})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'reply' in data
    assert len(data['reply']) > 0
    assert '📊' in data['reply']

def test_reaction_time_saving(client):
    """Save reaction test score to CSV and verify leaderboard"""
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    resp = client.post('/save_result', json={'fullName': 'Test Tester', 'reactionTime': 245.5})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get('reactionTime') == 245.5
    assert data.get('fullName') == 'Test Tester'
    assert 'leaderboard' in data

