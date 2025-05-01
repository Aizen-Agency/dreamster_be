from app.extensions.extension import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Wallet(db.Model):
    __tablename__ = 'wallets'
    
    id = db.Column(db.String(255), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    address = db.Column(db.String(255), nullable=False, unique=True)
    chain_type = db.Column(db.String(50), nullable=False)
    recovery_user_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('wallets', lazy=True))
    
    def __repr__(self):
        return f'<Wallet {self.address}>'
