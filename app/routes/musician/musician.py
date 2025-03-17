from flask import Blueprint, jsonify, request
from app.middleware.musician_auth import musician_required
from app.extensions.extension import db
from app.routes.user.user_utils import handle_errors
from http import HTTPStatus

musician_bp = Blueprint('musician', __name__, url_prefix='/api/musician')

@musician_bp.route('/profile', methods=['GET'])
@musician_required
@handle_errors
def get_musician_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role.name,
        'phone_number': current_user.phone_number,
        # Add musician-specific fields here
    }), HTTPStatus.OK

@musician_bp.route('/dashboard', methods=['GET'])
@musician_required
@handle_errors
def get_musician_dashboard(current_user):
    """Get the dashboard data for the authenticated musician."""
    # Musician-specific logic here
    return jsonify({
        'message': 'Musician dashboard data',
        'user_id': current_user.id
    }), HTTPStatus.OK 