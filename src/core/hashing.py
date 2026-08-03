# src/core/hashing.py
import bcrypt


def hash_password(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt natif.
    bcrypt est limité à 72 octets : on tronque proprement si besoin.
    """
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Vérifie un mot de passe contre son hash bcrypt.
    """
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)