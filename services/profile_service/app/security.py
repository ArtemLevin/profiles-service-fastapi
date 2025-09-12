from jose import jwt

def decode_jwt(token: str, *, secret: str, alg: str) -> dict:
    return jwt.decode(token, secret, algorithms=[alg])
