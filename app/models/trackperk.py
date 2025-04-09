from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
import enum

class PerkType(enum.Enum):
    text = "text"
    url = "url"
    file = "file"
    audio = "audio"

class TrackPerk(db.Model):
    __tablename__ = 'track_perks'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    track_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tracks.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = db.Column(db.Boolean, default=False)
    perk_type = db.Column(db.Enum(PerkType), default=PerkType.text)
    s3_url = db.Column(db.String, nullable=True)    
    track = db.relationship('Track', backref=db.backref('perks', lazy=True))