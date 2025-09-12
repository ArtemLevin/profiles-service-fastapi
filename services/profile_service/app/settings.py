from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "supersecretjwt"
    jwt_alg: str = "HS256"
    profiles_crypto_key_base64: str = "ZjJkM2Q0ZmVhYmNkZWZnaGlqa2xtbm9wcnN0dXYxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="  # 32 bytes
    phone_hash_pepper: str = "pepper"
    class Config:
        env_prefix = ""
        env_file = ".env"
        case_sensitive = False

settings = Settings()
