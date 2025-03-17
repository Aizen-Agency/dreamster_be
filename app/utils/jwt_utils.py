import os
from app.extensions.extension import jwt
from app.models.user import UserRole

@jwt.encode_key_loader
def get_jwt_secret_key(identity):
    from app.models.user import User
    
    # Get the user from the database
    user = User.query.get(identity)
    
    if not user or not user.role:
        # Default to a general secret key if no role is set
        return os.environ.get('JWT_SECRET_KEY', os.urandom(32))
    
    # Select the appropriate secret key based on role
    if user.role == UserRole.fan:
        return os.environ.get('FAN_SECRET_KEY')
    elif user.role == UserRole.musician:
        return os.environ.get('MUSICIAN_SECRET_KEY')
    elif user.role == UserRole.admin:
        return os.environ.get('ADMIN_SECRET_KEY')
    else:
        # Fallback to default secret key
        return os.environ.get('JWT_SECRET_KEY', os.urandom(32))

@jwt.decode_key_loader
def get_jwt_decode_key(jwt_header, jwt_data):
    """
    Returns the appropriate key for decoding based on the JWT payload.
    """
    # Extract the user identity from the token
    user_id = jwt_data.get('sub')  # 'sub' is the identity claim key
    
    # Get the user from the database
    from app.models.user import User
    user = User.query.get(user_id)
    
    if not user or not user.role:
        return os.environ.get('JWT_SECRET_KEY', os.urandom(32))
    
    # Select the appropriate secret key based on role
    if user.role == UserRole.fan:
        return os.environ.get('FAN_SECRET_KEY')
    elif user.role == UserRole.musician:
        return os.environ.get('MUSICIAN_SECRET_KEY')
    elif user.role == UserRole.admin:
        return os.environ.get('ADMIN_SECRET_KEY')
    else:
        return os.environ.get('JWT_SECRET_KEY', os.urandom(32)) 