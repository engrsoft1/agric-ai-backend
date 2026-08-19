import hashlib
import secrets
import hmac
from fastapi.security import HTTPBearer

bearer_scheme = HTTPBearer()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    """

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )

    return f"{salt}${password_hash.hex()}"


# ============================================================
# PASSWORD VERIFICATION
# ============================================================

def verify_password(
    plain_password: str,
    stored_password: str,
) -> bool:

    try:

        salt, stored_hash = stored_password.split("$", 1)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )

        return hmac.compare_digest(
            password_hash.hex(),
            stored_hash,
        )

    except (ValueError, AttributeError):

        return False