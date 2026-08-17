import hashlib
import secrets
import re

def normalize_identifier(value):
    return value.strip().lower()

def normalize_phone(value):
    return re.sub(r"[^\d+]", "", value.strip())

def validate_identifier(value):
    value = value.strip()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return "email", normalize_identifier(value)
    phone = normalize_phone(value)
    if re.fullmatch(r"\+?[1-9]\d{7,14}", phone):
        return "phone", phone
    return None, None

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 310_000
    )
    return digest.hex(), salt.hex()

def verify_password(password, stored_hash, salt_hex):
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 310_000
    )
    return secrets.compare_digest(digest.hex(), stored_hash)

def create_otp():
    return f"{secrets.randbelow(1_000_000):06d}"

def hash_otp(otp):
    salt = secrets.token_bytes(16)
    digest = hashlib.sha256(salt + otp.encode()).hexdigest()
    return digest, salt.hex()

def verify_otp(otp, stored_hash, salt_hex):
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.sha256(salt + otp.encode()).hexdigest()
    return secrets.compare_digest(digest, stored_hash)
