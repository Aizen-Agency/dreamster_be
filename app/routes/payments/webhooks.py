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
        return handle_successful_payment(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        return handle_failed_payment(payment_intent)
    elif event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        return handle_checkout_session_completed(session)
    
    return jsonify({'status': 'success'}), HTTPStatus.OK

def handle_checkout_session_completed(session):
    """Process completed checkout session"""
    # Extract payment intent from the session
    payment_intent_id = session.get('payment_intent')
    if not payment_intent_id:
        print(f"No payment intent in checkout session: {session.get('id')}")
        return jsonify({'status': 'success'}), HTTPStatus.OK
    
    # Fetch the payment intent to get complete details
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return handle_successful_payment(payment_intent)
    except Exception as e:
        print(f"Error processing checkout session: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error processing checkout session'}), HTTPStatus.INTERNAL_SERVER_ERROR

def handle_successful_payment(payment_intent):
    """Process successful payment without NFT minting"""
    payment_id = payment_intent['id']
    
    existing_transaction = Transaction.query.filter_by(payment_id=payment_id).first()
    if existing_transaction:
        print(f"Payment {payment_id} already processed")
        return jsonify({'status': 'success', 'message': 'Payment already processed'}), HTTPStatus.OK
    print("payment_intent", payment_intent)
    metadata = payment_intent.get('metadata', {})
    user_id = metadata.get('user_id')
    track_id = metadata.get('track_id')
    
    if not user_id or not track_id:
        print(f"Missing user_id or track_id in payment metadata: {metadata}")
        return jsonify({'status': 'error', 'message': 'Missing metadata'}), HTTPStatus.BAD_REQUEST
    
    try:
        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            track_id=uuid.UUID(track_id),
            amount=payment_intent['amount'] / 100,  
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
        
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Payment successful'}), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        # Log the error for investigation
        print(f"Error processing payment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), HTTPStatus.INTERNAL_SERVER_ERROR

def handle_failed_payment(payment_intent):
    """Process failed payment"""
    payment_id = payment_intent['id']
    
    # Check if this payment failure was already processed
    existing_transaction = Transaction.query.filter_by(payment_id=payment_id).first()
    if existing_transaction and existing_transaction.status == TransactionStatus.failed:
        print(f"Failed payment {payment_id} already processed")
        return jsonify({'status': 'success', 'message': 'Failed payment already processed'}), HTTPStatus.OK
    
    metadata = payment_intent.get('metadata', {})
    user_id = metadata.get('user_id')
    track_id = metadata.get('track_id')
    
    if not user_id or not track_id:
        print(f"Missing user_id or track_id in payment metadata: {metadata}")
        return jsonify({'status': 'error', 'message': 'Missing metadata'}), HTTPStatus.BAD_REQUEST
    
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

        return jsonify({'status': 'success', 'message': 'Payment failed'}), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        # Log the error
        print(f"Error recording failed payment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), HTTPStatus.INTERNAL_SERVER_ERROR 