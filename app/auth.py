from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from pathlib import Path

from pydantic import BaseModel, Field


SESSION_COOKIE = "myavatar_session"
PBKDF2_ITERATIONS = 600_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class AuthError(RuntimeError):
    pass


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.fullmatch(email):
        raise AuthError("Please enter a valid email address.")
    return email


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


class UserStore:
    """JSON-file-backed user accounts keyed by normalized email."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def register(self, email: str, password: str) -> str:
        email = normalize_email(email)
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        with self._lock:
            users = self._load()
            if email in users:
                raise AuthError("An account with this email already exists.")
            users[email] = {"password_hash": hash_password(password), "created_at": time.time()}
            self._save(users)
        return email

    def authenticate(self, email: str, password: str) -> str:
        try:
            email = normalize_email(email)
        except AuthError:
            raise AuthError("Invalid email or password.") from None
        with self._lock:
            record = self._load().get(email)
        if record is None or not verify_password(password, record.get("password_hash", "")):
            raise AuthError("Invalid email or password.")
        return email

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, users: dict[str, dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(users, indent=2), encoding="utf-8")
        tmp.replace(self.path)


class SessionSigner:
    """Issues and verifies HMAC-signed, expiring session tokens."""

    def __init__(self, secret: bytes, ttl_seconds: float):
        self._secret = secret
        self.ttl_seconds = ttl_seconds

    def create_token(self, email: str) -> str:
        payload = f"{_b64encode(email)}.{int(time.time() + self.ttl_seconds)}"
        return f"{payload}.{self._signature(payload)}"

    def verify_token(self, token: str | None) -> str | None:
        if not token:
            return None
        payload, _, signature = token.rpartition(".")
        if not payload or not hmac.compare_digest(self._signature(payload), signature):
            return None
        email_b64, _, expires = payload.rpartition(".")
        try:
            if int(expires) < time.time():
                return None
            return _b64decode(email_b64)
        except (ValueError, UnicodeDecodeError):
            return None

    def _signature(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def load_or_create_secret(env_value: str | None, path: Path) -> bytes:
    """Use MYAVATAR_SECRET_KEY when set; otherwise persist a random secret next to the storage dir."""
    if env_value:
        return env_value.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.write_bytes(secret)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return secret


def _b64encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def _b64decode(text: str) -> str:
    return base64.urlsafe_b64decode(text.encode("ascii")).decode("utf-8")
