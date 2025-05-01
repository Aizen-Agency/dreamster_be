from flask import Blueprint, request, jsonify
from app.extensions.extension import db, jwt
from app.models.user import User, UserRole
from app.config import Config
from app.services.privy_service import PrivyService
import datetime
import os
from flask_jwt_extended import create_access_token
from app.routes.auth.auth_utils import (
    validate_registration_input, 
    validate_login_input, 
    validate_role_input,
    handle_errors
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
@handle_errors
def register():
    data = request.get_json()
    
    # Validate input
    valid, message = validate_registration_input(data)
    if not valid:
        return jsonify({'message': message}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'message': 'Email already registered'}), 400
    
    # Check if phone number is provided and not empty
    phone_number = data.get('phone_number')
    if phone_number == '':
        phone_number = None
    
    # Check if phone number already exists (if provided)
    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return jsonify({'message': 'Phone number already registered'}), 400
    
    # Create new user
    user = User(
        username=data.get('username'),
        email=data.get('email'),
        phone_number=phone_number
    )
    user.password = data.get('password')
    
    db.session.add(user)
    db.session.commit()

    user = User.query.filter_by(email=data.get('email')).first()

    token = create_access_token(identity=user.id)

    privy_service = PrivyService()
    response = privy_service.create_wallet_address(user.email, user.id, token)
    if 'wallets' in response and len(response['wallets']) > 0:
        user.wallet_address = response['wallets'][0]['address']
        db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }), 201

@auth_bp.route('/set-role', methods=['POST'])
@handle_errors
def set_role():
    data = request.get_json()
    
    # Validate input
    valid, message = validate_role_input(data)
    if not valid:
        return jsonify({'message': message}), 400
    
    user_id = data.get('user_id')
    role = data.get('role')
    
    # Find user by ID
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Set role
    try:
        user_role = UserRole[role]
        user.role = user_role
        db.session.commit()
        
        # Generate a new token with the appropriate secret key
        new_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User role set successfully',
            'token': new_token,  # Include the new token
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': role
            }
        }), 200
    except KeyError:
        return jsonify({'message': 'Invalid role. Must be fan, musician, or admin'}), 400

@auth_bp.route('/login', methods=['POST'])
@handle_errors
def login():
    data = request.get_json()
    
    # Validate input
    valid, message = validate_login_input(data)
    if not valid:
        return jsonify({'message': message}), 400
    
    # Find user by email
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user or not user.verify_password(data.get('password')):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    token = create_access_token(identity=user.id)
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.name if user.role else None
        }
    }), 200