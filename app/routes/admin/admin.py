from flask import Blueprint, jsonify, request
from app.middleware.admin_auth import admin_required
from app.extensions.extension import db
from app.models.user import User
from app.routes.user.user_utils import handle_errors
from http import HTTPStatus

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/users', methods=['GET'])
@admin_required
@handle_errors
def get_all_users(current_user):
    """Get all users (admin only)."""
    users = User.query.all()
    user_list = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name if user.role else None
    } for user in users]
    
    return jsonify({
        'users': user_list
    }), HTTPStatus.OK

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
@handle_errors
def get_admin_dashboard(current_user):
    """Get the admin dashboard data."""
    # Admin-specific logic here
    return jsonify({
        'message': 'Admin dashboard data',
        'user_id': current_user.id
    }), HTTPStatus.OK 