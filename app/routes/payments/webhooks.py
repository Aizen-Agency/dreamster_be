from flask import Blueprint, request, jsonify
from http import HTTPStatus
import stripe
import os
from app.extensions.extension import db
from app.models.user import User
from app.models.track import Track
from app.models.transaction import Transaction, TransactionStatus
import json
import uuid

webhook_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')

# Initialize Stripe with your API key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

@webhook_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({'message': 'Invalid payload'}), HTTPStatus.BAD_REQUEST
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({'message': 'Invalid signature'}), HTTPStatus.BAD_REQUEST
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_successful_payment(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_failed_payment(payment_intent)
    
    return jsonify({'status': 'success'}), HTTPStatus.OK

def handle_successful_payment(payment_intent):
    """Process successful payment without NFT minting"""
    metadata = payment_intent.get('metadata', {})
    user_id = metadata.get('user_id')
    track_id = metadata.get('track_id')
    
    if not user_id or not track_id:
        return
    
    try:
        # Create transaction record
        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            track_id=uuid.UUID(track_id),
            amount=payment_intent['amount'] / 100,  # Convert cents to dollars
            payment_id=payment_intent['id'],
            status=TransactionStatus.completed
        )
        db.session.add(transaction)
        
        # Create user-track ownership record
        from app.models.user_owned_track import UserOwnedTrack
        ownership = UserOwnedTrack(
            user_id=uuid.UUID(user_id),
            track_id=uuid.UUID(track_id),
            transaction_id=transaction.id
        )
        db.session.add(ownership)
        
        # Update track sales count
        track = Track.query.get(uuid.UUID(track_id))
        if track:
            track.sales_count = Track.sales_count + 1
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log the error for investigation
        print(f"Error processing payment: {str(e)}")

def handle_failed_payment(payment_intent):
    """Process failed payment"""
    metadata = payment_intent.get('metadata', {})
    user_id = metadata.get('user_id')
    track_id = metadata.get('track_id')
    
    if not user_id or not track_id:
        return
    
    try:
        # Create failed transaction record
        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            track_id=uuid.UUID(track_id),
            amount=payment_intent['amount'] / 100,
            payment_id=payment_intent['id'],
            status=TransactionStatus.failed,
            error_message=payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
        )
        db.session.add(transaction)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log the error
        print(f"Error recording failed payment: {str(e)}") 