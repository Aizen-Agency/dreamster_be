from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class Collaborator(db.Model):
    __tablename__ = 'collaborators'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tracks.id'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    split_share = db.Column(db.Numeric, nullable=False)
    wallet_address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    track = db.relationship('Track', backref=db.backref('collaborators', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('track_collaborations', lazy='dynamic'))
    
    # Unique constraint to prevent duplicate collaborations
    __table_args__ = (
        db.UniqueConstraint('track_id', 'user_id', name='unique_track_user'),
        db.CheckConstraint('split_share > 0 AND split_share <= 100', name='check_split_share_range'),
    )