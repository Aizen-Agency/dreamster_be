from functools import wraps
from flask import request, jsonify, current_app
from app.models.user import User
from app.config import Config
import os
from app.extensions.extension import jwt

secret_key = Config.SECRET_KEY or os.urandom(32)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            payload = jwt.decode(token, jwk_key, do_verify=True)
            
            current_user = User.query.get(payload['sub'])
            
            if not current_user:
                return jsonify({'message': 'Invalid token: User not found'}), 401
                
        except JWTDecodeError as e:
            return jsonify({'message': f'Invalid token: {str(e)}'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated 