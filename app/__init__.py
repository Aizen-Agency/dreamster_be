from flask import Flask
from flask_migrate import Migrate
import os
from app.extensions.extension import jwt, db
from flask_cors import CORS
from datetime import timedelta

# Initialize migrate with the imported db
migrate = Migrate()

def create_app(config_name='default'):
    from app.config import config_by_name
    
    # Initialize app
    app = Flask(__name__)
    CORS(app)

    app.config.from_object(config_by_name[config_name])
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=3)
    
    app.config['JWT_ALGORITHM'] = os.environ.get('JWT_ALGORITHM', 'RS256')
    
    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # # Configure CORS based on environment
    # if app.config['ENV'] == 'production':
    #     # Production CORS settings - restrict to specific origins
    #     allowed_origins = app.config.get('ALLOWED_ORIGINS', ['https://dreamster-fe.vercel.app', 'https://dreamster-fe.vercel.app/'])
    #     CORS(app, resources={r"/*": {
    #         "origins": allowed_origins.split(','),
    #         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    #         "allow_headers": ["Content-Type", "Authorization"],
    #         "supports_credentials": True
    #     }})
    # else:
    #     # Development CORS settings - allow all origins
    #     CORS(app, resources={r"/*": {
    #         "origins": "*", 
    #         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    #         "allow_headers": ["Content-Type", "Authorization"],
    #         "content-type": "*"
    #     }})
    
    # Import JWT utils to register the loaders
    from app.utils import jwt_utils
    
    # Register blueprints
    from app.routes.user import user_bp
    from app.routes.auth import auth_bp
    from app.routes.musician import musician_bp
    from app.routes.auth.recovery import recovery_bp
    from app.routes.musician.tracks.tracks import tracks_bp
    from app.routes.tracks.public_tracks import public_tracks_bp
    from app.routes.tracks.stream import stream_bp
    from app.routes.admin.admin import admin_bp
    from app.routes.tracks.likes import likes_bp
    from app.routes.admin.track_approval import track_approval_bp
    from app.routes.admin.track_management import track_management_bp
    from app.routes.musician.tracks.collaborators import collaborators_bp
    from app.routes.musician.tracks.share import share_bp
    from app.routes.payments.stripe import payments_bp
    from app.routes.payments.webhooks import webhook_bp
    from app.routes.user.library import library_bp
    from app.routes.user.perks import perks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(musician_bp)
    app.register_blueprint(tracks_bp)
    app.register_blueprint(recovery_bp)
    app.register_blueprint(public_tracks_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(likes_bp)
    app.register_blueprint(track_approval_bp)
    app.register_blueprint(track_management_bp)
    app.register_blueprint(collaborators_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(perks_bp)
        
    @app.route('/')
    def index():
        return "Welcome to the API"
    
    from app.models.user import User, UserRole
    from app.models.track import Track
    from app.models.trackperk import TrackPerk
    from app.models.collaborator import Collaborator
    from app.models.deleted_track import DeletedTrack
    # from app.models.wallets import Wallet

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