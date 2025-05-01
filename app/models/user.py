from app.extensions.extension import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum
import uuid
from sqlalchemy.dialects.postgresql import UUID

class UserRole(enum.Enum):
    fan = "fan"
    musician = "musician"
    admin = "admin"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=True)
    profile_picture_url = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    wallet_address = db.Column(db.String(), nullable=True, unique=True)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

    def get_liked_tracks(self, page=1, per_page=10):
        """Get tracks liked by this user with pagination"""
        from app.models.track_like import TrackLike
        from app.models.track import Track
        
        liked_tracks = TrackLike.query.filter_by(
            user_id=self.id
        ).order_by(
            TrackLike.created_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return liked_tracks 