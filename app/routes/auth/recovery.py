from flask import Blueprint, request, jsonify
from app.extensions.extension import db
from app.models.user import User
from app.models.verification import VerificationCode
from app.services.email_service import EmailService
from app.routes.auth.auth_utils import handle_errors
from http import HTTPStatus
import logging

# Set up logging
logger = logging.getLogger(__name__)

recovery_bp = Blueprint('recovery', __name__, url_prefix='/api/auth/recovery')
email_service = EmailService()

@recovery_bp.route('/request-reset', methods=['POST'])
@handle_errors
def request_password_reset():
    """
    Request a password reset by providing an email address.
    Sends a verification code to the user's email if it exists.
    """
    data = request.get_json()
    
    if not data or 'email' not in data:
        return jsonify({'message': 'Email is required'}), HTTPStatus.BAD_REQUEST
    
    email = data['email']
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Don't reveal that the email doesn't exist for security reasons
        return jsonify({'message': 'If your email exists in our system, you will receive a verification code'}), HTTPStatus.OK
    
    # Generate verification code
    verification = VerificationCode.generate_code(user.id, 'password_reset')
    
    # Send email with verification code
    subject = "Password Reset Verification - Dreamster"
    body = f"Your verification code for Dreamster password reset is: {verification.code}\n\nThis code will expire in 15 minutes."
    
    email_sent = email_service.send_email(email, subject, body)
    
    if not email_sent:
        return jsonify({'message': 'Failed to send verification code'}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    logger.info(f"Password reset verification code sent to {email}")
    return jsonify({'message': 'Verification code sent to your email'}), HTTPStatus.OK

@recovery_bp.route('/verify-code', methods=['POST'])
@handle_errors
def verify_code():
    """
    Verify the code sent to the user's email for password reset.
    """
    data = request.get_json()
    
    if not data or 'email' not in data or 'code' not in data:
        return jsonify({'message': 'Email and verification code are required'}), HTTPStatus.BAD_REQUEST
    
    email = data['email']
    code = data['code']
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Invalid email or verification code'}), HTTPStatus.BAD_REQUEST
    
    # Find the most recent unused verification code for this user
    verification = VerificationCode.query.filter_by(
        user_id=user.id,
        code=code,
        purpose='password_reset',
        is_used=False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if not verification or not verification.is_valid():
        return jsonify({'message': 'Invalid or expired verification code'}), HTTPStatus.BAD_REQUEST
    
    # Generate a temporary token for password reset
    # This token will be used in the next step to reset the password
    reset_verification = VerificationCode.generate_code(user.id, 'password_reset_confirmed', expiry_minutes=30)
    
    # Mark the verification code as used
    verification.mark_as_used()
    
    return jsonify({
        'message': 'Verification successful',
        'reset_token': reset_verification.code
    }), HTTPStatus.OK

@recovery_bp.route('/reset-password', methods=['POST'])
@handle_errors
def reset_password():
    """
    Reset the user's password after verification.
    """
    data = request.get_json()
    
    if not data or 'email' not in data or 'reset_token' not in data or 'new_password' not in data:
        return jsonify({'message': 'Email, reset token, and new password are required'}), HTTPStatus.BAD_REQUEST
    
    email = data['email']
    reset_token = data['reset_token']
    new_password = data['new_password']
    
    # Validate password
    if len(new_password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters long'}), HTTPStatus.BAD_REQUEST
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Invalid email or reset token'}), HTTPStatus.BAD_REQUEST
    
    # Find the reset token
    verification = VerificationCode.query.filter_by(
        user_id=user.id,
        code=reset_token,
        purpose='password_reset_confirmed',
        is_used=False
    ).first()
    
    if not verification or not verification.is_valid():
        return jsonify({'message': 'Invalid or expired reset token'}), HTTPStatus.BAD_REQUEST
    
    # Update the password
    user.password = new_password
    
    # Mark the verification code as used
    verification.mark_as_used()
    
    # Save changes
    db.session.commit()
    
    logger.info(f"Password reset successful for user {user.id}")
    return jsonify({'message': 'Password has been reset successfully'}), HTTPStatus.OK 