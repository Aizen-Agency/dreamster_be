from flask import Flask
from flask_migrate import Migrate
import os
from app.extensions.extension import jwt, db
from flask_cors import CORS

# Initialize migrate with the imported db
migrate = Migrate()

def create_app(config_name='default'):
    from app.config import config_by_name
    
    # Initialize app
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.user import user_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    
    # Apply CORS
    CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
                         "allow_headers": ["Content-Type", "Authorization"]}})
    
    @app.route('/')
    def index():
        return "Welcome to the API"
    
    # Import all models before creating tables
    from app.models.user import User, UserRole
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

# Function to drop all tables (for reset operations)
def drop_all_tables():
    with create_app().app_context():
        db.drop_all()

# Create the application instance
app = create_app(os.getenv('FLASK_ENV', 'default'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
