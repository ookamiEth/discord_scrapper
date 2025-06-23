"""
Secure user token management with encryption
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import hashlib
import aiohttp
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean

from database import Base
from datetime import datetime

class UserToken(Base):
    """Encrypted user token storage"""
    __tablename__ = "user_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)
    encrypted_token = Column(Text, nullable=False)
    token_hash = Column(String(64))  # SHA-256 hash for identification
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_valid = Column(Boolean, default=True)
    last_validation = Column(DateTime)  # Track when last validated

class TokenManager:
    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Generate from environment or create new
            key = os.getenv('TOKEN_ENCRYPTION_KEY')
            if not key:
                key = Fernet.generate_key().decode()
                print(f"Generated new encryption key: {key}")
                print("Add this to your .env file as TOKEN_ENCRYPTION_KEY")
            self.cipher = Fernet(key.encode())
    
    def encrypt_token(self, token: str) -> Tuple[str, str]:
        """Encrypt token and return encrypted value + hash"""
        encrypted = self.cipher.encrypt(token.encode()).decode()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return encrypted, token_hash
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt token"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    def store_user_token(self, db: Session, user_id: str, token: str):
        """Store encrypted user token"""
        encrypted, token_hash = self.encrypt_token(token)
        
        # Check if token exists
        existing = db.query(UserToken).filter(UserToken.user_id == user_id).first()
        if existing:
            existing.encrypted_token = encrypted
            existing.token_hash = token_hash
            existing.last_used = datetime.utcnow()
            existing.last_validation = datetime.utcnow()
        else:
            new_token = UserToken(
                user_id=user_id,
                encrypted_token=encrypted,
                token_hash=token_hash,
                last_validation=datetime.utcnow()
            )
            db.add(new_token)
        
        db.commit()
    
    def get_user_token(self, db: Session, user_id: str) -> Optional[str]:
        """Retrieve and decrypt user token"""
        token_record = db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.is_valid == True
        ).first()
        
        if token_record:
            token_record.last_used = datetime.utcnow()
            db.commit()
            return self.decrypt_token(token_record.encrypted_token)
        
        return None


async def validate_discord_token(token: str) -> Tuple[bool, Optional[str]]:
    """Validate token with minimal API interaction"""
    try:
        # Use aiohttp instead of discord.py to minimize footprint
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://discord.com/api/v9/users/@me',
                headers={'Authorization': token}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data.get('id')
                return False, None
    except Exception:
        return False, None