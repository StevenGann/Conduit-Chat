import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    pwd = password.encode("utf-8")
    if len(pwd) > 72:
        import hashlib
        pwd = hashlib.sha256(pwd).digest()
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pwd = plain.encode("utf-8")
    if len(pwd) > 72:
        import hashlib
        pwd = hashlib.sha256(pwd).digest()
    return bcrypt.checkpw(pwd, hashed.encode("utf-8"))


def create_access_token(subject: str, is_bot: bool = False) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": subject, "exp": expire, "is_bot": is_bot}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def generate_api_token() -> str:
    return secrets.token_urlsafe(32)
