from app.models import db
from app.models.user import User
from flask import jsonify, Blueprint, request
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.user import Plan, Subscription
import stripe
import os

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')  # Make sure this environment variable is set

api_SelectPlan_Page = Blueprint("api_SelectPlan_Page", __name__, url_prefix="")

@api_SelectPlan_Page.route('/create-subscription', methods=['POST'])
def create_subscription():
    print("Entering create_subscription function")
    data = request.get_json()
    if not data:
        print("No JSON data received")
        return jsonify({"error": "No data provided"}), 400

    username = data.get('username')
    plan_id = data.get('plan_id')
    price_id = data.get('price_id')
    payment_method_id = data.get('payment_method_id')

    print(
        f"Received data: username={username}, plan_id={plan_id}, price_id={price_id}, payment_method_id={payment_method_id}")

    if not all([username, plan_id, price_id, payment_method_id]):
        print("Missing required fields")
        return jsonify({"error": "Missing required fields"}), 400

    user = User.query.filter_by(username=username).first()
    plan = Plan.query.filter_by(stripe_price_id=price_id).first()
    print(f"Plan usage limit: {plan.usage_limit}")
    
    if not user or not plan:
        print(f"User or Plan not found: user={user}, plan={plan}")
        return jsonify({"error": "User or Plan not found"}), 404

    try:
        print("Starting subscription creation process")
        # Create or get Stripe customer
        if not user.stripe_customer_id:
            print("Creating new Stripe customer")
            customer = stripe.Customer.create(
                email=user.email,
                payment_method=payment_method_id,
            )
            user.stripe_customer_id = customer.id
            db.session.commit()
        else:
            print("Retrieving existing Stripe customer")
            customer = stripe.Customer.retrieve(user.stripe_customer_id)

        print(f"Attaching PaymentMethod {payment_method_id} to customer {customer.id}")
        try:
            # Attach PaymentMethod to customer
            stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
        except stripe.error.InvalidRequestError as e:
            if "already been attached" not in str(e):
                raise

        print("Setting default payment method for customer")
        # Set the default payment method on the customer
        stripe.Customer.modify(
            customer.id,
            invoice_settings={'default_payment_method': payment_method_id},
        )

        print("Creating Stripe subscription")
        # Create Stripe subscription with automatic payment
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': price_id}],
            default_payment_method=payment_method_id,
            expand=['latest_invoice.payment_intent'],
            off_session=True,
            payment_settings={'save_default_payment_method': 'on_subscription'}
        )

        print(f"Initial subscription status: {stripe_subscription.status}")
        print(f"Latest invoice status: {stripe_subscription.latest_invoice.status}")
        
        if stripe_subscription.latest_invoice.payment_intent:
            payment_intent = stripe_subscription.latest_invoice.payment_intent
            print(f"Payment intent status: {payment_intent.status}")
            
            if payment_intent.status == 'requires_payment_method':
                print("Confirming payment intent")
                payment_intent = stripe.PaymentIntent.confirm(
                    payment_intent.id,
                    payment_method=payment_method_id,
                    off_session=True
                )
                print(f"Payment intent status after confirmation: {payment_intent.status}")
            
            if payment_intent.status == 'requires_action':
                return jsonify({
                    'status': 'requires_action',
                    'payment_intent_client_secret': payment_intent.client_secret,
                    'subscription_id': stripe_subscription.id
                }), 200

        # Retrieve the updated subscription
        stripe_subscription = stripe.Subscription.retrieve(stripe_subscription.id)
        print(f"Final subscription status: {stripe_subscription.status}")

        if stripe_subscription.status not in ['active', 'trialing']:
            return jsonify({
                'error': 'Subscription activation failed',
                'status': stripe_subscription.status,
                'payment_intent_status': payment_intent.status if payment_intent else 'unknown'
            }), 400

        print("Creating or updating local subscription record")
        # Check for existing subscription
        existing_subscription = Subscription.query.filter_by(user_id=user.id).first()
        
        if existing_subscription:
            print(f"Updating existing subscription: {existing_subscription.id}")
            existing_subscription.stripe_subscription_id = stripe_subscription.id
            existing_subscription.plan_id = plan.id
            existing_subscription.status = stripe_subscription.status
            existing_subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            existing_subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            existing_subscription.updated_at = datetime.utcnow()
            existing_subscription.usage_count = 0  # Reset usage count for new subscription
        else:
            print("Creating new subscription record")
            existing_subscription = Subscription(
                user_id=user.id,
                stripe_subscription_id=stripe_subscription.id,
                plan_id=plan.id,
                status=stripe_subscription.status,
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
            )
            db.session.add(existing_subscription)

        db.session.commit()

        print(f"Subscription created/updated successfully: {existing_subscription.id}")
        return jsonify({
            'status': 'succeeded',
            'message': 'Subscription created successfully',
            'subscription_id': existing_subscription.id,
            'stripe_subscription_id': stripe_subscription.id
        }), 201

    except stripe.error.CardError as e:
        print(f"Card error: {e.error.message}")
        return jsonify({"error": e.error.message}), 400
    except stripe.error.RateLimitError as e:
        print("Rate limit error")
        return jsonify({"error": "Rate limit exceeded"}), 429
    except stripe.error.InvalidRequestError as e:
        print(f"Invalid request error: {str(e)}")
        return jsonify({"error": "Invalid parameters"}), 400
    except stripe.error.AuthenticationError as e:
        print("Authentication error")
        return jsonify({"error": "Authentication failed"}), 401
    except stripe.error.APIConnectionError as e:
        print("API connection error")
        return jsonify({"error": "Network error"}), 500
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({"error": "Something went wrong"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_SelectPlan_Page.route('/users/<username>/usages', methods=['GET'])
def get_user_usages(username):
    print(f"Fetching usage for user: {username}")
    try:
        user = User.query.filter_by(username=username).first()
        print(f"User query result: {user}")

        if not user:
            print(f"User not found: {username}")
            return jsonify({'error': 'User not found'}), 404

        # Fetch the user's active subscription and associated plan
        subscription = Subscription.query.filter_by(user_id=user.id).first()
        print(f"Active subscription for user: {subscription}")
        if not subscription:
            print(f"No active subscription found for user: {username}")
            return jsonify({'error': 'Active subscription not found'}), 404

        plan = Plan.query.filter_by(id=subscription.plan_id).first()
        print(f"Plan for subscription: {plan}")
        if not plan:
            print(f"Plan not found for subscription: {subscription.id}")
            return jsonify({'error': 'Plan not found'}), 404

        # Calculate remaining usage
        if plan.usage_limit:
            remaining_usage = plan.usage_limit - subscription.usage_count
            print(f"Remaining usage: {remaining_usage}")
        else:
            remaining_usage = "Unlimited"  # No usage limit for this plan
            print("Unlimited usage plan")

        print(f"Returning remaining usage for user {username}: {remaining_usage}")
        return jsonify({'remaining_usages': remaining_usage}), 200

    except Exception as e:
        print(f"Error in get_user_usages: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_SelectPlan_Page.route('/subscription/<int:user_id>', methods=['GET'])
def get_subscription(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    subscription = user.subscription
    if not subscription:
        return jsonify({"error": "No active subscription found"}), 404

    return jsonify({
        "subscription_id": subscription.id,
        "status": subscription.status,
        "plan": subscription.plan.name,
        "current_period_end": subscription.current_period_end.isoformat()
    }), 200


@api_SelectPlan_Page.route('/cancel-subscription/<int:user_id>', methods=['POST'])
def cancel_subscription(user_id):
    user = User.query.get(user_id)
    if not user or not user.subscription:
        return jsonify({"error": "User or subscription not found"}), 404

    try:
        stripe.Subscription.delete(user.subscription.stripe_subscription_id)
        user.subscription.status = 'canceled'
        db.session.commit()
        return jsonify({"message": "Subscription canceled successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_SelectPlan_Page.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'invoice.payment_succeeded':
        handle_successful_payment(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_failed_payment(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_canceled(event['data']['object'])

    return jsonify(success=True), 200


def handle_successful_payment(invoice):
    subscription = Subscription.query.filter_by(stripe_subscription_id=invoice['subscription']).first()
    if subscription:
        subscription.status = 'active'
        subscription.current_period_end = datetime.fromtimestamp(invoice['lines']['data'][0]['period']['end'])
        db.session.commit()


def handle_failed_payment(invoice):
    subscription = Subscription.query.filter_by(stripe_subscription_id=invoice['subscription']).first()
    if subscription:
        subscription.status = 'past_due'
        db.session.commit()


def handle_subscription_canceled(subscription_object):
    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_object['id']).first()
    if subscription:
        subscription.status = 'canceled'
        db.session.commit()

@api_SelectPlan_Page.route('/api/users/<username>', methods=['GET'])
def get_user(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_subaccount": user.is_subaccount,
            "has_subscription": user.subscription is not None
        }), 200
    except Exception as e:
        print(f"Error fetching user data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@api_SelectPlan_Page.route('/api/users/<username>/subscription', methods=['GET'])
def get_user_subscription(username):
    print(f"Fetching subscription data for username: {username}")
    try:
        user = User.query.filter_by(username=username).first()
        print(f"Found user: {user}")
        print(f"User ID: {user.id if user else None}")
        
        if not user:
            print("User not found")
            return jsonify({"error": "User not found"}), 404

        # Get all subscriptions for debugging
        all_subscriptions = Subscription.query.all()
        print(f"All subscriptions in database: {[sub.id for sub in all_subscriptions]}")

        subscription = Subscription.query.filter_by(user_id=user.id).first()
        print(f"Found subscription: {subscription}")
        print(f"Subscription ID: {subscription.id if subscription else None}")

        if not subscription:
            # Get all plans for debugging
            all_plans = Plan.query.all()
            print(f"All plans in database: {[plan.id for plan in all_plans]}")
            return jsonify({"error": "No subscription found", "user_id": user.id}), 404

        plan = Plan.query.get(subscription.plan_id)
        print(f"Found plan: {plan}")
        print(f"Plan details: ID={plan.id}, Name={plan.name}")

        response_data = {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "plan": {
                "name": plan.name,
                "description": plan.description,
                "price": plan.price,
                "interval": plan.interval,
                "usage_limit": plan.usage_limit
            },
            "usage_count": subscription.usage_count,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat()
        }
        
        print(f"Returning response data: {response_data}")
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error in get_user_subscription: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@api_SelectPlan_Page.route('/api/users/<username>/subscription/cancel', methods=['POST'])
def cancel_user_subscription(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        subscription = user.subscription
        if not subscription:
            return jsonify({"error": "No active subscription found"}), 404

        # Cancel the subscription in Stripe
        stripe_subscription = stripe.Subscription.delete(
            subscription.stripe_subscription_id
        )

        # Update local subscription status
        subscription.status = 'canceled'
        db.session.commit()

        return jsonify({
            "message": "Subscription canceled successfully",
            "status": subscription.status
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error canceling subscription: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@api_SelectPlan_Page.route('/api/users/<username>/payment-method', methods=['GET'])
def get_payment_method(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user or not user.stripe_customer_id:
            return jsonify({"error": "User not found or no payment method"}), 404

        # Get customer's default payment method
        customer = stripe.Customer.retrieve(
            user.stripe_customer_id,
            expand=['invoice_settings.default_payment_method']
        )
        
        payment_method = customer.invoice_settings.default_payment_method
        if not payment_method:
            return jsonify({"error": "No payment method found"}), 404

        return jsonify({
            "last4": payment_method.card.last4,
            "brand": payment_method.card.brand,
            "exp_month": payment_method.card.exp_month,
            "exp_year": payment_method.card.exp_year
        }), 200

    except Exception as e:
        print(f"Error fetching payment method: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@api_SelectPlan_Page.route('/api/users/<username>/payment-method', methods=['POST'])
def update_payment_method(username):
    try:
        data = request.get_json()
        payment_method_id = data.get('payment_method_id')
        
        if not payment_method_id:
            return jsonify({"error": "Payment method ID is required"}), 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.stripe_customer_id:
            return jsonify({"error": "User not found"}), 404

        # Attach new payment method to customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=user.stripe_customer_id,
        )

        # Set as default payment method
        stripe.Customer.modify(
            user.stripe_customer_id,
            invoice_settings={'default_payment_method': payment_method_id},
        )

        return jsonify({"message": "Payment method updated successfully"}), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error updating payment method: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

