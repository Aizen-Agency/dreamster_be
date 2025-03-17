# app/routes/user/user_utils.py
import re
from flask import jsonify, Blueprint, request
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
from app.extensions.extension import db
from http import HTTPStatus

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

def validate_user_update(data):
    if 'username' in data and len(data['username']) < 3:
        return False, "Username must be at least 3 characters long"
    
    if 'email' in data:
        valid_email = re.match(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,3}$', data['email'])
        if not valid_email:
            return False, "Email is not valid"
    
    if 'phone_number' in data and data['phone_number'] and data['phone_number'] != '':
        valid_phone = re.match(r'^\+?[0-9]{10,15}$', data['phone_number'])
        if not valid_phone:
            return False, "Phone number is not valid"
    
    if 'password' in data and len(data['password']) < 6:
        return False, "Password must be at least 6 characters long"
    
    return True, None

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # Use Flask-JWT-Extended's built-in verification
            verify_jwt_in_request()
            
            # Get the user ID from the JWT
            user_id = get_jwt_identity()
            print(f"JWT identity: {user_id}")  # Debug log
            
            # Get the user from the database
            current_user = User.query.get(user_id)
            
            if not current_user:
                print(f"User not found for ID: {user_id}")  # Debug log
                return jsonify({'message': 'Invalid token: User not found'}), 401
                
        except Exception as e:
            print(f"Token verification error: {str(e)}")  # Debug log
            return jsonify({'message': f'Invalid token: {str(e)}'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@user_bp.route('/profile', methods=['GET'])
@token_required
@handle_errors
def get_profile(current_user):
    """Get the profile of the authenticated user.
    
    Returns:
        JSON response with user profile data
    """
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role.name if current_user.role else None,
        'phone_number': current_user.phone_number
    }), HTTPStatus.OK

@user_bp.route('/update', methods=['PUT'])
@token_required
@handle_errors
def update_user(current_user):
    """Update the authenticated user's profile.
    
    Returns:
        JSON response with updated user data or error message
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST
    
    # Validate input
    valid, message = validate_user_update(data)
    if not valid:
        return jsonify({'message': message}), HTTPStatus.BAD_REQUEST
    
    try:
        # Check if phone number is being updated and already exists
        if 'phone_number' in data and data['phone_number'] != current_user.phone_number:
            # Handle empty string for phone_number
            if data['phone_number'] == '':
                data['phone_number'] = None
            elif User.query.filter_by(phone_number=data['phone_number']).first():
                return jsonify({'message': 'Phone number already registered'}), HTTPStatus.CONFLICT
        
        # Update user fields
        if 'username' in data:
            current_user.username = data['username']
        if 'phone_number' in data:
            current_user.phone_number = data['phone_number']
        if 'password' in data:
            current_user.password = data['password']
        
        # Save changes
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role.name if current_user.role else None,
                'phone_number': current_user.phone_number
            }
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        # Log the error but don't expose details to client
        print(f"Error updating user: {str(e)}")
        return jsonify({'message': 'An error occurred while updating user'}), HTTPStatus.INTERNAL_SERVER_ERROR