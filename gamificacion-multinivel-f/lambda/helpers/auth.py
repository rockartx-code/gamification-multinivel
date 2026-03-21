import hashlib
import random


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def generate_otp_code(length: int = 6) -> str:
    return "".join(random.choices("0123456789", k=length))
