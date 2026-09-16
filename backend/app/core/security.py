from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import hmac
import hashlib
import bcrypt
from jose import jwt, JWTError
from cryptography.fernet import Fernet
from app.core.config import settings

# Fernet cipher for symmetric token encryption
_cipher: Optional[Fernet] = None

def get_fernet() -> Fernet:
    global _cipher
    if _cipher is None:
        try:
            _cipher = Fernet(settings.FERNET_KEY.encode())
        except Exception:
            # Fallback for dev if invalid key provided
            key = Fernet.generate_key()
            _cipher = Fernet(key)
    return _cipher

def get_password_hash(password: str) -> str:
    # Truncate password to 72 bytes for bcrypt compatibility
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def encrypt_token(plain_token: str) -> str:
    """Encrypt sensitive OAuth token before storing in database."""
    cipher = get_fernet()
    return cipher.encrypt(plain_token.encode('utf-8')).decode('utf-8')

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt stored OAuth token for server-side GitHub API calls."""
    cipher = get_fernet()
    return cipher.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')

def verify_github_signature(payload_bytes: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Validate GitHub webhook HMAC-SHA256 signature (X-Hub-Signature-256).
    Header format: sha256=<hex_digest>
    """
    if not signature_header or not secret:
        return False
    
    parts = signature_header.split("sha256=")
    if len(parts) != 2:
        return False
    
    expected_hash = parts[1].strip()
    mac = hmac.new(secret.encode('utf-8'), msg=payload_bytes, digestmod=hashlib.sha256)
    computed_hash = mac.hexdigest()
    
    return hmac.compare_digest(computed_hash, expected_hash)
