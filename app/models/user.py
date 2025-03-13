from . import db
from sqlalchemy import Boolean, String, Text, ForeignKey, func, Integer, DateTime
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    parent_username = db.Column(db.String(150), ForeignKey('user.username'), nullable=True)
    is_subaccount = db.Column(db.Boolean, default=False)
    subaccounts = db.relationship(
        'User',
        backref=db.backref('parent', remote_side=[username]),
        foreign_keys=[parent_username]
    )
    email = db.Column(db.String(150), unique=True, nullable=False)  # Add this line


    # New fields for subscription
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True)
    subscription = db.relationship('Subscription', backref='user', uselist=False)




class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='active')
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    usage_count = db.Column(db.Integer, default=0)  # Number of times the user has used the service in the current period


class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stripe_price_id = db.Column(db.String(255), unique=True, nullable=False)
    interval = db.Column(db.String(20), nullable=False)  # 'month' or 'year'
    usage_limit = db.Column(db.Integer, nullable=True)  # Add usage limit (null for unlimited)
    subscriptions = db.relationship('Subscription', backref='plan')

#     class Agent(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     # Add any other fields needed for your Agent model
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# class PhoneNumber(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     number = db.Column(db.String(20), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     # Add any other fields needed for your PhoneNumber model
#     is_primary = db.Column(db.Boolean, default=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
