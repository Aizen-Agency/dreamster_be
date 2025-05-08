from flask import Blueprint, jsonify, request
from app.utils.auth import token_required
from app.extensions.extension import db
from app.models.user import User
from app.routes.user.user_utils import validate_user_update, handle_errors
from app.services.s3_service import S3Service
from http import HTTPStatus
import logging
from functools import wraps
import os

# Set up logging
logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/api/user')
s3_service = S3Service(bucket_name='dreamster-users')

@user_bp.route('/<uuid:user_id>', methods=['GET'])
@token_required
@handle_errors
def get_user_by_id(current_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name if user.role else None,
        'avatar': user.profile_picture_url if user.profile_picture_url else None,
        'phone_number': user.phone_number,
        'created_at': user.created_at,
        'updated_at': user.updated_at,
        'wallet_address': user.wallet_address,
        # 'bio': user.bio if user.bio else None,
        # 'location': user.location if user.location else None,
        # 'website': user.website if user.website else None,
        # 'social_links': user.social_links if user.social_links else None
    }), HTTPStatus.OK

@user_bp.route('/profile', methods=['GET'])
@token_required
@handle_errors
def get_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role.name if current_user.role else None,
        'phone_number': current_user.phone_number,
        'profile_picture_url': current_user.profile_picture_url,
        'wallet_address': current_user.wallet_address
    }), HTTPStatus.OK

@user_bp.route('/update', methods=['PUT'])
@token_required
@handle_errors
def update_user(current_user):
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
                'phone_number': current_user.phone_number,
                'profile_picture_url': current_user.profile_picture_url,
                'wallet_address': current_user.wallet_address
            }
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user {current_user.id}: {str(e)}")
        return jsonify({'message': 'An error occurred while updating user'}), HTTPStatus.INTERNAL_SERVER_ERROR 

@user_bp.route('/profile-picture', methods=['POST'])
@token_required
@handle_errors
def upload_profile_picture(current_user):
    """Upload a profile picture for the current user"""
    logger.info(f"Profile picture upload requested for user ID: {current_user.id}")
    
    # Check if file is present in request
    if 'profile_picture' not in request.files:
        return jsonify({'message': 'No profile picture provided'}), HTTPStatus.BAD_REQUEST
    
    profile_picture = request.files['profile_picture']
    
    # Check if filename is empty
    if profile_picture.filename == '':
        return jsonify({'message': 'No profile picture selected'}), HTTPStatus.BAD_REQUEST
    
    # Check file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    file_extension = os.path.splitext(profile_picture.filename)[1].lower()
    if file_extension not in allowed_extensions:
        return jsonify({'message': 'File type not allowed. Please upload a JPG, PNG or GIF image'}), HTTPStatus.BAD_REQUEST
    
    try:
        # Upload to S3
        profile_url = s3_service.upload_profile_picture(profile_picture, current_user.id)
        
        # Update user record
        current_user.profile_picture_url = profile_url
        db.session.commit()
        
        logger.info(f"Profile picture uploaded successfully for user ID: {current_user.id}")
        
        return jsonify({
            'message': 'Profile picture uploaded successfully',
            'profile_picture_url': profile_url
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading profile picture for user {current_user.id}: {str(e)}")
        return jsonify({'message': f'Error uploading profile picture: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function 