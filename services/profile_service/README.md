

Сервис профилей пользователей: CRUD профиля с PII (шифрование телефона AES-256-GCM, hash телефона с pepper), JWT-аутентификация, валидация номера (E.164). В комплекте — Dockerfile, миграция Alembic и автотесты (pytest, httpx).

## Запуск (локально)
```bash


python -m venv .venv && source .venv/bin/activate


pip install -r requirements.txt



export DATABASE_URL=sqlite+aiosqlite:///./dev.db   # для локальной отладки
export JWT_SECRET=supersecretjwt
export JWT_ALG=HS256
export PROFILES_CRYPTO_KEY_BASE64=ZjJkM2Q0ZmVhYmNkZWZnaGlqa2xtbm9wcnN0dXYxMjM0NTY3ODkwMTIzNDU2Nzg5MA==  
export PHONE_HASH_PEPPER=my_pepper

alembic upgrade head  

uvicorn app.main:app --reload --port 8010
```

## Запуск через Docker
```bash
docker build -t profile-service:phase1 .
docker run --rm -p 8010:8000 \
  -e DATABASE_URL='postgresql+asyncpg://cinema:cinema@db:5432/profiles_db' \
  -e JWT_SECRET='supersecretjwt' -e JWT_ALG='HS256' \
  -e PROFILES_CRYPTO_KEY_BASE64='...' -e PHONE_HASH_PEPPER='...' \
  profile-service:phase1
```

## Тесты
```bash

pytest -q
```
