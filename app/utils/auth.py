from functools import wraps
from flask import request, jsonify, current_app
from app.models.user import User
from app.config import Config
import os
from app.extensions.extension import jwt
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

secret_key = Config.SECRET_KEY or os.urandom(32)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # Use Flask-JWT-Extended's built-in verification
            verify_jwt_in_request()
            
            # Get the user ID from the JWT
            user_id = get_jwt_identity()
            
            # Get the user from the database
            current_user = User.query.get(user_id)
            
            if not current_user:
                return jsonify({'message': 'Invalid token: User not found'}), 401
                
        except Exception as e:
            return jsonify({'message': f'Invalid token: {str(e)}'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated 