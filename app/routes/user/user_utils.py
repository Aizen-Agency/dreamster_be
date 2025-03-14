# app/routes/user/user_utils.py
import re
from flask import jsonify
from functools import wraps

def validate_user_update(data):
    if 'username' in data and len(data['username']) < 3:
        return False, "Username must be at least 3 characters long"
    
    if 'email' in data:
        valid_email = re.match(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,3}$', data['email'])
        if not valid_email:
            return False, "Email is not valid"
    
    if 'phone_number' in data:
        valid_phone = re.match(r'^\+?[0-9]{10,15}$', data['phone_number'])
        if not valid_phone:
            return False, "Phone number is not valid"
    
    return True, None

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function