from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url_profiles: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "supersecretjwt"
    jwt_alg: str = "HS256"
    profiles_crypto_key_base64: str = "npKbpZeqEz7YCeTmRnh+W/tVCAq9lavsjDsuT9yyz2o="  # 32 bytes
    phone_hash_pepper: str = "pepper"
    redis_host: str = "localhost"
    redis_port: int = 6379

    class Config:
        env_prefix = ""
        env_file = "../../../.env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()