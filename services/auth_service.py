import hashlib
import secrets


def hash_password(password):
    salt = secrets.token_hex(16)
    iterations = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password, stored):
    if not stored:
        return False
    if str(stored).startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, saved_digest = str(stored).split("$", 3)
            digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
            return secrets.compare_digest(digest, saved_digest)
        except Exception:
            return False
    return secrets.compare_digest(str(stored), hashlib.sha256(str(password).encode("utf-8")).hexdigest())
