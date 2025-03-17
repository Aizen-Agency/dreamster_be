import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-key-for-testing'
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv('STAGING_DATABASE_URL')
    
    # SendGrid Email configuration
    SENDGRID_API_KEY = os.environ.get('TWILIO_API_KEY', '')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@yourdomain.com')
    SENDER_NAME = os.environ.get('SENDER_NAME', 'Dreamster App')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DEVELOPMENT_DATABASE_URL') or os.getenv('STAGING_DATABASE_URL')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TESTING_DATABASE_URL') or os.getenv('STAGING_DATABASE_URL')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('PRODUCTION_DATABASE_URL') or os.getenv('STAGING_DATABASE_URL')

class StagingConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('STAGING_DATABASE_URL')

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}