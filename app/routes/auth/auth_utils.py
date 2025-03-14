# app/routes/auth/auth_utils.py
import re
from flask import jsonify
from functools import wraps

def validate_registration_input(data):
    if not all(key in data for key in ('username', 'email', 'password')):
        return False, "Missing required fields"
    
    if len(data.get('username', '')) < 3:
        return False, "Username must be at least 3 characters long"
    
    # Email validation
    email = data.get('email', '')
    valid_email = re.match(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,3}$', email)
    if not valid_email:
        return False, "Email is not valid"
    
    if len(data.get('password', '')) < 6:
        return False, "Password must be at least 6 characters long"
    
    return True, None

def validate_login_input(data):
    if not all(key in data for key in ('email', 'password')):
        return False, "Missing required fields"
    return True, None

def validate_role_input(data):
    if not all(key in data for key in ('user_id', 'role')):
        return False, "Missing required fields"
    
    valid_roles = ['fan', 'musician']
    if data.get('role') not in valid_roles:
        return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
    
    return True, None

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function