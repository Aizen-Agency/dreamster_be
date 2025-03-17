from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User, UserRole

def musician_required(f):
    """
    Middleware that checks if the current user has the musician role.
    If not, it returns a 403 Forbidden response.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # Verify JWT is present and valid
            verify_jwt_in_request()
            
            # Get the user ID from the JWT
            user_id = get_jwt_identity()
            
            # Get the user from the database
            current_user = User.query.get(user_id)
            
            if not current_user:
                return jsonify({'message': 'Invalid token: User not found'}), 401
            
            # Check if the user has the musician role
            if not current_user.role or current_user.role != UserRole.musician:
                return jsonify({
                    'message': 'Access denied: Musician role required'
                }), 403
                
            # User has musician role, proceed with the endpoint
            return f(current_user, *args, **kwargs)
            
        except Exception as e:
            return jsonify({'message': f'Authentication error: {str(e)}'}), 401
    
    return decorated 