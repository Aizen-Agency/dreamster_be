from app.extensions.extension import db
from datetime import datetime, timedelta
import random
import string

class VerificationCode(db.Model):
    __tablename__ = 'verification_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'password_reset', 'email_verification', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    @classmethod
    def generate_code(cls, user_id, purpose, expiry_minutes=15):
        """Generate a new verification code for a user"""
        # Generate a random 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Create new verification code
        verification = cls(
            user_id=user_id,
            code=code,
            purpose=purpose,
            expires_at=expires_at
        )
        
        # Save to database
        db.session.add(verification)
        db.session.commit()
        
        return verification
    
    def is_valid(self):
        """Check if the verification code is still valid"""
        return (not self.is_used and 
                datetime.utcnow() <= self.expires_at)
    
    def mark_as_used(self):
        """Mark the verification code as used"""
        self.is_used = True
        db.session.commit() 