"""
Security and Cryptography Utilities
====================================
Provides:
- Argon2id password hashing and verification
- Strong password policy enforcement
- Cryptographically secure random token generation and hashing
"""

import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Configure Argon2id password hasher
# Default parameters meet RFC 9106 recommended settings for interactive logins
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    Returns True if valid, False otherwise.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate that password meets security requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    return True, ""


def generate_random_token(bytes_len: int = 32) -> tuple[str, str]:
    """
    Generate a cryptographically secure random token and its SHA-256 hash.
    Returns:
        (raw_token, token_hash)
    """
    raw_token = secrets.token_urlsafe(bytes_len)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """Compute the SHA-256 hexadecimal digest of an opaque token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
