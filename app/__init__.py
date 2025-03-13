from flask import Flask
from flask_cors import CORS
from .config import DevelopmentConfig
from .models import db
from dotenv import load_dotenv
from sqlalchemy import inspect
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# from app.routes.routes_googleauth.routes_googleauth import api_googlecalendar_Page
from .routes.routes_auth import api_login
from .routes.routes_SelectPlan_Page.routes_SelectPlan_Page import api_SelectPlan_Page
from .routes.routes_utilities import api_bp
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse
from app.models.user import Plan, User, Subscription

import os


def initialize_plans():
    plans = [
            {
        "name": "Individual",
        "description": "Best for individual enterprise",
        "price": 192.99,  # 20% discount for yearly plan
        "stripe_price_id": "price_1QH8TX02khdf3R0AlBJjp5Ll",  # Yearly price ID
        "interval": "year",
        "usage_limit": 1  # 1 agent limit
    },
    {
        "name": "Individual Monthly",
        "description": "Best for individual enterprise",
        "price": 19.99,  # Monthly price
        "stripe_price_id": "price_1QH8TX02khdf3R0AJUTGTXIR",  # Monthly price ID
        "interval": "month",
        "usage_limit": 1  # 1 agent limit
    },
    # Agency Plans
    {
        "name": "Agency",
        "description": "Perfect for agencies and growing businesses",
        "price": 2399.99,  # 20% discount for yearly plan
        "stripe_price_id": "price_1QH8VF02khdf3R0AnAjoGqGy",  # Yearly price ID
        "interval": "year",
        "usage_limit": 3  # 3 agents limit
    },
    {
        "name": "Agency Monthly",
        "description": "Perfect for agencies and growing businesses",
        "price": 249.99,  # Monthly price
        "stripe_price_id": "price_1QH8UP02khdf3R0AfcfXmAoR",  # Monthly price ID
        "interval": "month",
        "usage_limit": 3  # 3 agents limit
    }
    
    ]

    for plan_data in plans:
        existing_plan = Plan.query.filter_by(stripe_price_id=plan_data['stripe_price_id']).first()
        if not existing_plan:
            new_plan = Plan(
                name=plan_data['name'],
                description=plan_data['description'],
                price=plan_data['price'],
                stripe_price_id=plan_data['stripe_price_id'],
                interval=plan_data['interval'],
                usage_limit=plan_data.get('usage_limit')  # Set usage limit

            )
            db.session.add(new_plan)
    
    db.session.commit()


def drop_all_tables():
    load_dotenv()
    uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    result = urlparse(uri)
    conn_params = {
        'dbname': result.path.lstrip('/'),
        'user': result.username,
        'password': result.password,
        'host': result.hostname,
        'port': result.port
    }

    try:
        # Connect to the database
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cursor:
                # Disable foreign key checks
                cursor.execute("SET CONSTRAINTS ALL DEFERRED;")

                # Get all tables in the public schema
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
                tables = cursor.fetchall()

                # Drop each table
                for table in tables:
                    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table[0])))
                    print(f"Dropped table: {table[0]}")

                # Re-enable foreign key checks
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")

            # Commit the changes
            conn.commit()
        print("All tables have been dropped successfully.")
    except psycopg2.Error as e:
        print(f"An error occurred while dropping tables: {e}")

def check_schema_changes(app):
    """
    Checks if there are any differences between the models and database schema.
    Returns True if changes are detected, False otherwise.
    """
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Get all models from db.Model
            models = db.Model.__subclasses__()
            model_tables = [model.__tablename__ for model in models]
            
            # Check for missing or extra tables
            missing_tables = set(model_tables) - set(existing_tables)
            extra_tables = set(existing_tables) - set(model_tables)
            
            if missing_tables or extra_tables:
                print("Schema changes detected:")
                if missing_tables:
                    print(f"Missing tables: {missing_tables}")
                if extra_tables:
                    print(f"Extra tables: {extra_tables}")
                return True
                
            # Check columns for each model
            for model in models:
                if model.__tablename__ in existing_tables:
                    columns = {c['name'] for c in inspector.get_columns(model.__tablename__)}
                    model_columns = {c.key for c in model.__table__.columns}
                    
                    if columns != model_columns:
                        print(f"Column differences detected in table {model.__tablename__}:")
                        print(f"Missing columns: {model_columns - columns}")
                        print(f"Extra columns: {columns - model_columns}")
                        return True
            
            print("No schema changes detected.")
            return False
            
    except Exception as e:
        print(f"Error checking schema changes: {e}")
        return None

def initialize_default_user():
    # Create default user
    default_email = "a@gmail.com"
    default_password = "1"
    hashed_password = generate_password_hash(default_password, method='pbkdf2:sha256')
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=default_email).first()
    if existing_user:
        print(f"Default user {default_email} already exists")
        return
    
    default_user = User(
        username=default_email,
        email=default_email,
        password=hashed_password
    )
    
    db.session.add(default_user)
    db.session.flush()  # This will assign an ID to default_user
    
    # Get the Individual Monthly plan
    default_plan = Plan.query.filter_by(name="Individual Monthly").first()
    
    if default_plan:
        # Create a subscription for the default user
        subscription = Subscription(
            user_id=default_user.id,
            stripe_subscription_id="default_subscription",
            status="active",
            plan_id=default_plan.id,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            usage_count=0
        )
        
        db.session.add(subscription)
    
    db.session.commit()
    print(f"Created default user: {default_email} with subscription")


def create_app():
    load_dotenv()
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    # CORS(app, resources={
    #     r"/*": {
    #         "origins": "*",
    #         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    #         "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    #         "expose_headers": ["Content-Range", "X-Content-Range"],
    #         "supports_credentials": True,
    #         "max_age": 600,
    #         "send_wildcard": False
    #     }
    # })
    # CORS(app, 
    # resources={r"/*": {
    #     "origins": ["http://localhost:3000", "https://aizen-crm-frontend-hmci.vercel.app"],  # Specify exact origins
    #     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    #     "allow_headers": ["Content-Type", "Authorization"],  # Added Authorization header
    #     "supports_credentials": True
    # }})




    app.config.from_object(DevelopmentConfig)  # Load development config

    db.init_app(app)

    # uri="postgres://udak05j6j87jdg:p0d625c18fe2ea5a3c03d51076ca0ea2f2e3003d0acd7c118df00ac535396f581@c5hilnj7pn10vb.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d10vr5oaanqd9t"
    app.register_blueprint(api_login)
    app.register_blueprint(api_SelectPlan_Page)

    app.register_blueprint(api_bp)

    with app.app_context():
        # Check for schema changes
        has_changes = True
        has_changes = check_schema_changes(app)
        # db.drop_all()
        # drop_all_tables()
        if has_changes:
            print("Database schema needs to be updated!")
            # db.drop_all()
            drop_all_tables()
            db.create_all() 
            initialize_plans()
            initialize_default_user()

        else:
            print("No schema changes detected.")

    return app

app = create_app()




