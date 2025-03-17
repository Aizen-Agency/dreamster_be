from flask import Blueprint, jsonify, request
from app.utils.auth import token_required
from app.extensions.extension import db
from app.models.user import User
from app.routes.user.user_utils import validate_user_update, handle_errors
from http import HTTPStatus
import logging
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/profile', methods=['GET'])
@token_required
@handle_errors
def get_profile(current_user):
    """Get the profile of the authenticated user."""
    logger.info(f"Profile requested for user ID: {current_user.id}")
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
    """Update the authenticated user's profile."""
    logger.info(f"Update requested for user ID: {current_user.id}")
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST
    
    # Validate input
    valid, message = validate_user_update(data)
    if not valid:
        return jsonify({'message': message}), HTTPStatus.BAD_REQUEST
    
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
    
    try:
        # Save changes
        db.session.commit()
        logger.info(f"User {current_user.id} updated successfully")
        
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
        logger.error(f"Error updating user {current_user.id}: {str(e)}")
        return jsonify({'message': 'An error occurred while updating user'}), HTTPStatus.INTERNAL_SERVER_ERROR 

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function 