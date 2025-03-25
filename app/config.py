import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-key-for-testing'
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Get DATABASE_URL with SSL mode required and fix potential Heroku postgres:// format
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url:
        # Add sslmode=require if not already present
        if 'sslmode=' not in db_url:
            db_url = f"{db_url}{'?' if '?' not in db_url else '&'}sslmode=require"
        # Replace postgres:// with postgresql:// for SQLAlchemy compatibility
        db_url = db_url.replace('postgres://', 'postgresql://')
    
    SQLALCHEMY_DATABASE_URI = db_url
    
    # SendGrid Email configuration
    SENDGRID_API_KEY = os.environ.get('TWILIO_API_KEY', '')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@yourdomain.com')
    SENDER_NAME = os.environ.get('SENDER_NAME', 'Dreamster App')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DEVELOPMENT_DATABASE_URL') or os.getenv('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TESTING_DATABASE_URL') or os.getenv('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('PRODUCTION_DATABASE_URL') or os.getenv('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI:
        # Add sslmode=require if not already present
        if SQLALCHEMY_DATABASE_URI and 'sslmode=' not in SQLALCHEMY_DATABASE_URI:
            SQLALCHEMY_DATABASE_URI = f"{SQLALCHEMY_DATABASE_URI}{'?' if '?' not in SQLALCHEMY_DATABASE_URI else '&'}sslmode=require"
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')

class StagingConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI:
        # Add sslmode=require if not already present
        if 'sslmode=' not in SQLALCHEMY_DATABASE_URI:
            SQLALCHEMY_DATABASE_URI = f"{SQLALCHEMY_DATABASE_URI}{'?' if '?' not in SQLALCHEMY_DATABASE_URI else '&'}sslmode=require"
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}