from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class TrackLike(db.Model):
    __tablename__ = 'track_likes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tracks.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create a unique constraint to prevent duplicate likes
    __table_args__ = (
        db.UniqueConstraint('user_id', 'track_id', name='uq_user_track_like'),
    )
    
    # Relationships
    user = db.relationship('User', backref=db.backref('liked_tracks', lazy='dynamic'))
    track = db.relationship('Track', backref=db.backref('user_likes', lazy='dynamic')) 