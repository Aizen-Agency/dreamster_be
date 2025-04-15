from flask import Blueprint, request, jsonify
from http import HTTPStatus
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions.extension import db
from app.models.user import User
from app.models.track import Track
from app.routes.user.user_utils import handle_errors
import stripe
import os
import uuid

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Initialize Stripe with your API key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@payments_bp.route('/create-payment-intent', methods=['POST'])
@jwt_required()
@handle_errors
def create_payment_intent():
    """Create a payment intent for purchasing a track"""
    data = request.get_json()
    
    # Validate input
    if not data or 'track_id' not in data:
        return jsonify({'message': 'Track ID is required'}), HTTPStatus.BAD_REQUEST
    
    # Get current user
    current_user = User.query.get(get_jwt_identity())
    if not current_user:
        return jsonify({'message': 'User not found'}), HTTPStatus.NOT_FOUND
    
    # Get track
    track_id = data['track_id']
    try:
        track_id = uuid.UUID(track_id) if isinstance(track_id, str) else track_id
    except ValueError:
        return jsonify({'message': 'Invalid track ID format'}), HTTPStatus.BAD_REQUEST
    
    track = Track.query.get(track_id)
    if not track or not track.approved:
        return jsonify({'message': 'Track not found or not available for purchase'}), HTTPStatus.NOT_FOUND
    
    # Calculate amount in cents (Stripe uses smallest currency unit)
    amount = int(float(track.starting_price) * 100)
    if amount <= 0:
        return jsonify({'message': 'Invalid track price'}), HTTPStatus.BAD_REQUEST
    
    try:
        # Create a PaymentIntent with the order amount and currency
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            metadata={
                'user_id': str(current_user.id),
                'track_id': str(track_id),
                'track_title': track.title
            }
        )
        
        return jsonify({
            'clientSecret': payment_intent.client_secret,
            'amount': amount,
            'track': {
                'id': str(track.id),
                'title': track.title,
                'artist': current_user.username,
                'price': float(track.starting_price)
            }
        })
    
    except Exception as e:
        return jsonify({'message': f'Error creating payment: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR 