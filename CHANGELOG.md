# [0.1.0] — 2025-09-13 — MVP сервиса профилей

### Добавлено
- **Новый микросервис `profile_service` (FastAPI)** с CRUD для владельца:
  - `POST /api/profile`
  - `GET  /api/profile/me`
  - `PUT  /api/profile`
  - `DELETE /api/profile`
- **Безопасное хранение PII**:
  - Телефон нормализуется в **E.164** и шифруется **AES-256-GCM** (`PROFILES_CRYPTO_KEY_BASE64`, 32 байта в base64).
  - Дополнительно хранится **phone_hash** (SHA-256 + `PHONE_HASH_PEPPER`) для индексации/уникальности.
- **JWT-аутентификация**: локальная проверка HS256; `sub` — числовой `user_id`.
- **Alembic-миграция**: таблица `profiles` с уникальными индексами на `user_id` и `phone_hash`.
- **Health & Docs**:
  - `GET /health`
  - Swagger: `GET /api/profile/openapi`

### Изменено / Интеграции
- **Gateway (Nginx)**: добавлен роут `/api/profile/` на `profile-service:8000` (**без завершающего слэша** в `proxy_pass`).
- **Compose**: добавлен сервис `profile-service` с переменными окружения и зависимостью от `db`.
- **.env**:
  - `DATABASE_URL_PROFILES=postgresql+asyncpg://cinema:cinema@db:5432/profiles_db`
  - `JWT_SECRET`, `JWT_ALG` (должны совпадать с auth-service)
  - `PROFILES_CRYPTO_KEY_BASE64` (32 байта base64), `PHONE_HASH_PEPPER`

### Тесты
- Набор `pytest` + `httpx`:
  - Позитивный CRUD-сценарий.
  - Валидация телефона (E.164) и обработка конфликтов (`409` на дублирование телефона/профиля).
- Быстрые тесты на in-memory SQLite; переопределение зависимостей для DI-сессии.

### Поведение API
- Коды ошибок: `401` (некорректный токен), `404` (профиль не найден), `409` (конфликт), `422` (невалидный телефон).
- В ответе для владельца — расшифрованный телефон (E.164).

### Операционные заметки
- Применяйте миграции Alembic при деплое (`alembic upgrade head`).
- Для локальной разработки допустим SQLite; в составе стека используйте Postgres `profiles_db` (убедитесь, что БД создана).

### Безопасность
- Секреты — только из ENV; не коммитить реальные ключи.
- Телефон всегда хранится в зашифрованном виде; hash используется только для поиска/уникальности.

### Руководство по миграции
1. Создайте БД `profiles_db` в общем Postgres (или добавьте init SQL).
2. В `docker-compose.yml` добавьте сервис **profile-service** и переменные окружения.
3. В `gateway/nginx.conf` добавьте:
   ```nginx
   location /api/profile/ { proxy_pass http://profile-service:8000; }

---

### Запланировано — Избранное и Рейтинги
- **Избранное**: таблица `favorites(profile_id, film_id, created_at)`, уникальный ключ `(profile_id, film_id)`; API: `POST/DELETE/GET /api/profile/me/favorites` (идемпотентно), пагинация.
- **Рейтинги**: таблица `ratings(profile_id, film_id, rating 1..10 с шагом 0.5)`, уникальный `(profile_id, film_id)`; API: `PUT /api/profile/me/ratings`, `GET /api/profile/me/ratings?film_id`.
- **Агрегаты**: публичный `GET /api/profile/public/films/{id}/rating-agg` → `{avg_rating, ratings_count}`; Redis TTL ≈ 300 сек; инвалидация при изменении собственного рейтинга.

### Запланировано — Отзывы, Модерация, Админка, Аудит
- **Отзывы**: таблица `reviews(profile_id, film_id, title?, body, rating?, status)`; CRUD владельца + публичный список по фильму.
- **Модерация**: админ-эндпоинты смены статуса (`published|hidden|moderation`) с RBAC.
- **Админ-панель**: read-only просмотр профилей (PII замаскированы), права `profiles.view_sensitive`.
- **Аудит и защита**: таблица `audit_logs` для доступа к PII; rate limiting (Redis) для приватных и публичных ручек.
- **Документация**: примеры в OpenAPI и Postman-коллекция.

---

#