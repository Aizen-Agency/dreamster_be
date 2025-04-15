from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class UserOwnedTrack(db.Model):
    __tablename__ = 'user_owned_tracks'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tracks.id'), nullable=False)
    transaction_id = db.Column(UUID(as_uuid=True), db.ForeignKey('transactions.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('owned_tracks', lazy=True))
    track = db.relationship('Track', backref=db.backref('owners', lazy=True))
    transaction = db.relationship('Transaction', backref=db.backref('ownership', lazy=True))
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'track_id', name='uq_user_track'),
    ) 