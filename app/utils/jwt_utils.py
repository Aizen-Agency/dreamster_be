import os
import logging
from app.extensions.extension import jwt
from app.models.user import UserRole, User

logger = logging.getLogger(__name__)

def read_key_file(file_path):
    try:
        with open(file_path, 'r') as key_file:
            return key_file.read()
    except Exception as e:
        logger.error(f"Failed to read key file {file_path}: {str(e)}")
        raise

@jwt.encode_key_loader
def get_jwt_encode_key(identity):
    user = User.query.get(identity)
    
    private_key_path = os.environ.get('JWT_PRIVATE_KEY_PATH', 'app/ssl/private_key.pem')
    
    if not user or not user.role:
        return read_key_file(private_key_path)
    
    jwt.additional_claims_callback = lambda: {"role": user.role.value}
    
    return read_key_file(private_key_path)

@jwt.decode_key_loader
def get_jwt_decode_key(jwt_header, jwt_data):
    public_key_path = os.environ.get('JWT_PUBLIC_KEY_PATH', 'app/ssl/public_key.pem')
    return read_key_file(public_key_path) 