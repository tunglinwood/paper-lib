"""Authentication helpers for Paper Library.

Adapted from ppt_index login function:
- PBKDF2-SHA256 password hashing
- JWT access tokens
- FastAPI dependency for current user / admin checks
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db import get_db

# --- Config ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

security = HTTPBearer(auto_error=False)


# --- Password hashing ---
def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-SHA256."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"pbkdf2:sha256:100000:{salt}:{password_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its PBKDF2-SHA256 hash."""
    try:
        algorithm, hash_name, iterations, salt, stored_hash = password_hash.split(":")
        if algorithm != "pbkdf2" or hash_name != "sha256":
            return False
        iterations = int(iterations)
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return secrets.compare_digest(computed_hash.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False


# --- User DB helpers ---
def get_user_by_username(username: str):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, email, is_admin FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, email, is_admin FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(username: str, password: str, email: Optional[str] = None, is_admin: bool = False):
    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return {"success": False, "error": "Username already exists"}

        password_hash = hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)",
            (username, password_hash, email or "", 1 if is_admin else 0),
        )
        conn.commit()
        return {"success": True, "user_id": cursor.lastrowid}
    finally:
        conn.close()


def update_last_login(user_id: int):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET last_login = datetime('now') WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


# --- JWT ---
def create_access_token(user_id: int, username: str, is_admin: bool) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "is_admin": is_admin,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# --- FastAPI dependencies ---
def _extract_token(request: Request) -> Optional[str]:
    # Authorization: Bearer <token>
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]

    # Cookie: access_token=<token>
    cookie = request.headers.get("cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("access_token="):
            return part[len("access_token="):]

    return None


async def get_current_user(request: Request) -> Optional[dict]:
    token = _extract_token(request)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = get_user_by_id(int(user_id))
    if not user:
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_admin": bool(user["is_admin"]),
    }


async def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# --- Default admin seed ---
def ensure_default_admin():
    """Create a default admin user if no users exist."""
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0 and DEFAULT_ADMIN_USERNAME and DEFAULT_ADMIN_PASSWORD:
            password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
            conn.execute(
                "INSERT INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)",
                (DEFAULT_ADMIN_USERNAME, password_hash, "", 1),
            )
            conn.commit()
            print(f"Created default admin user: {DEFAULT_ADMIN_USERNAME}")
    finally:
        conn.close()
