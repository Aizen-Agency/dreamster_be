import os
import uuid
from random import choice
from flask import Blueprint, Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from app.models import db
from app.models.user import User, Plan, Subscription
import jwt
from datetime import datetime, timedelta

load_dotenv()  # This loads the environment variables from .env file

api_login = Blueprint("login", __name__, url_prefix="")






@api_login.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(username=email).first():
        print("Email already exists")
        return jsonify({"error": "Email already registered"}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=email, email=email, password=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201



@api_login.route('/login', methods=['POST'])
def login():
    print("Login route accessed")
    data = request.get_json()
    print(f"Received data: {data}")

    username = data['username']
    password = data['password']
    print(f"Attempting login for user: {username}")

    user = User.query.filter_by(username=username).first()
    print(f"User found: {user is not None}")

    if not user or not check_password_hash(user.password, password):
        print("Invalid username or password")
        return jsonify({"error": "Invalid username or password"}), 400

    print("Login successful")
    # Check if user has any subscription
    has_subscription = user.subscription is not None
    print(f"User has subscription: {has_subscription}")

    return jsonify({
        "message": f"Welcome {user.username}!",
        "username": user.username,
        "success": True,
        "has_subscription": has_subscription,
        "is_subaccount": user.is_subaccount
    }), 200



@api_login.route('/create-subaccount', methods=['POST'])
def create_subaccount():
    print("Create subaccount route accessed")
    data = request.get_json()
    print(f"Received data: {data}")
    
    parent_username = data.get('parent_username')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', username)
    print(f"Parent username: {parent_username}, Username: {username}, Email: {email}")

    if not all([parent_username, username, password]):
        print("Missing required fields")
        return jsonify({"error": "Missing required fields"}), 400

    # Check if parent exists
    parent_user = User.query.filter_by(username=parent_username).first()
    print(f"Parent user found: {parent_user is not None}")
    if not parent_user:
        print("Parent account not found")
        return jsonify({"error": "Parent account not found"}), 404

    # Check if username is already taken
    if User.query.filter_by(username=username).first():
        print("Username already exists")
        return jsonify({"error": "Username already exists"}), 400

    # Create the subaccount
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_subaccount = User(
        username=username,
        password=hashed_password,
        parent_username=parent_username,
        is_subaccount=True,
        email=email
    )
    print(f"New subaccount created: {new_subaccount}")

    try:
        db.session.add(new_subaccount)
        db.session.commit()
        print("Subaccount created successfully")
        return jsonify({
            "message": "Subaccount created successfully",
            "subaccount": {
                "id": new_subaccount.id,
                "username": username,
                "email": email,
                "parent_username": parent_username
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating subaccount: {e}")
        return jsonify({"error": str(e)}), 500



@api_login.route('/subaccounts/<parent_username>', methods=['GET'])
def get_subaccounts(parent_username):
    try:
        subaccounts = User.query.filter_by(parent_username=parent_username).all()
        return jsonify({
            "subaccounts": [{
                "id": subaccount.id,
                "username": subaccount.username,
                "created_at": subaccount.created_at.isoformat() if hasattr(subaccount, 'created_at') else None
            } for subaccount in subaccounts]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@api_login.route('/api/user-dashboard/<username>', methods=['GET'])
def get_user_dashboard_data(username):
    try:
        # Get user
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Get agents
        agents = Agent.query.filter_by(user_id=user.id).all()
        
        # Get phone numbers
        phone_numbers = PhoneNumber.query.filter_by(user_id=user.id).all()
        
        return jsonify({
            "user": {
                "username": user.username,
                "email": user.email,
                "parent_username": user.parent_username,
                "is_subaccount": user.is_subaccount,
                "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
            },
            "agents": [{
                "id": agent.id,
                "description": agent.description,
                "website": agent.website,
                "created_at": agent.created_at.isoformat()
            } for agent in agents],
            "phone_numbers": [{
                "id": number.id,
                "phone_number": number.phone_number,
                "country": number.country,
                "created_at": number.timestamp.isoformat()
            } for number in phone_numbers]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500