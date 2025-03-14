from flask import Blueprint, jsonify
from app.utils.auth import token_required

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role.name if current_user.role else None,
        'phone_number': current_user.phone_number
    }), 200 