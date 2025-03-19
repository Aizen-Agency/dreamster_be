from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

class Genre(enum.Enum):
    electronic = "electronic"
    lofi = "lofi"
    synthwave = "synthwave"
    hiphop = "hiphop"                              
    rock = "rock"
    pop = "pop"
    ambient = "ambient"                            
    jazz = "jazz"                               

class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    genre = db.Column(db.Enum(Genre))
    tags = db.Column(JSONB)
    starting_price = db.Column(db.Numeric, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    s3_url = db.Column(db.String)
    artist_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False) 
    duration = db.Column(db.Integer)
    stream_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    
