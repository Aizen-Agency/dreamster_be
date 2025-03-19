from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class TrackPerk(db.Model):
    __tablename__ = 'track_perks'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String, nullable=True)
    track_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tracks.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = db.Column(db.Boolean, default=False)
    
    track = db.relationship('Track', backref=db.backref('perks', lazy=True))