from app.extensions.extension import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

class TransactionStatus(enum.Enum):
    pending = 'pending'
    completed = 'completed'
    failed = 'failed'
    refunded = 'refunded'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tracks.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_id = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.pending)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    track = db.relationship('Track', backref=db.backref('transactions', lazy=True)) 
    