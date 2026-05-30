"""
Authentication — login and registration logic.
Passwords hashed with bcrypt (industry standard, never stored in plaintext).
"""

import bcrypt
from src.database import get_user, create_user


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, pw_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8"))
    except Exception:
        return False


def login(username: str, password: str) -> tuple[bool, dict | None, str]:
    """
    Returns (success, user_dict, error_message).
    user_dict is None on failure.
    """
    username = username.strip().lower()
    if not username or not password:
        return False, None, "Please enter your username and password."
    user = get_user(username)
    if not user:
        return False, None, "Username not found. Please register first."
    if not verify_password(password, user["password_hash"]):
        return False, None, "Incorrect password. Please try again."
    return True, user, ""


def register(
    username: str, email: str, password: str, confirm: str,
    name: str, age: str, blood_group: str, conditions: str,
) -> tuple[bool, dict | None, str]:
    """
    Returns (success, user_dict, error_message).
    """
    username = username.strip().lower()
    if not username:
        return False, None, "Username is required."
    if len(username) < 3:
        return False, None, "Username must be at least 3 characters."
    if not password:
        return False, None, "Password is required."
    if len(password) < 6:
        return False, None, "Password must be at least 6 characters."
    if password != confirm:
        return False, None, "Passwords do not match."
    if get_user(username):
        return False, None, "Username already taken. Please choose another."
    pw_hash = hash_password(password)
    user = create_user(username, email.strip(), pw_hash,
                       name.strip(), age.strip(), blood_group.strip(), conditions.strip())
    return True, user, ""
