https://github.com/ArtemLevin/graduate_work/tree/develop

Online Cinema

## Содержание
- [Архитектура и сервисы](#архитектура-и-сервисы)
  - [Инфраструктурные зависимости](#инфраструктурные-зависимости)
- [Требования](#требования)
- [Подготовка окружения](#подготовка-окружения)
  - [Ключевые переменные окружения](#ключевые-переменные-окружения)
  - [Генерация секретов профиля](#генерация-секретов-профиля)
- [Первый запуск](#первый-запуск)
  - [Проверка готовности](#проверка-готовности)
- [Локальная разработка и качество](#локальная-разработка-и-качество)
  - [Частный запуск сервисов](#частный-запуск-сервисов)
- [Наблюдаемость и эксплуатация](#наблюдаемость-и-эксплуатация)
- [API и документация](#api-и-документация)
- [Миграции и данные](#миграции-и-данные)
- [Типичные проблемы](#типичные-проблемы)
- [Дополнительные материалы](#дополнительные-материалы)


---

## Архитектура и сервисы

| Сервис | Стек | Основные зависимости | Базовые эндпоинты через gateway |
| ------ | ---- | -------------------- | ------------------------------- |
| `gateway` | Nginx 1.25 | обратное проксирование на сервисы | `/health`, `/api/<svc>/…` |
| `auth_service` | FastAPI, SQLAlchemy, JWT | PostgreSQL/SQLite, asyncpg/aiosqlite | `/api/auth/register`, `/api/auth/login`, `/api/auth/me` |
| `content_api` | FastAPI | Elasticsearch 8, Redis 7 | `/api/content/films`, `/api/content/genres`, `/api/content/persons` |
| `profile_service` | FastAPI, Alembic, SlowAPI | PostgreSQL, Redis, AES-GCM шифрование PII | `/api/profile/me`, `/api/profile/me/favorites`, `/api/profile/public/films/{id}/rating-agg` |
| `ugc_service` | FastAPI | ClickHouse HTTP API (fallback in-memory storage) | `/api/ugc/events`, `/api/ugc/event`, `/health` |
| `admin_panel` | Django 4 | PostgreSQL | `/admin/` |

### Инфраструктурные зависимости

* **PostgreSQL 15** — базы `auth_db`, `admin_db`, `profiles_db`.
* **Redis 7** — кэш контента и профилей, rate limiting.
* **Elasticsearch 8** — индексы фильмов, жанров, персон.
* **ClickHouse 23.3** — события UGC (просмотры, рейтинги и т.д.).
* **Docker Compose** соединяет сервисы и gateway; Makefile предоставляет короткие команды.

Все FastAPI-приложения используют общий пакет `services/common` для логирования, метрик, трассировки и rate limiting, а `prometheus_fastapi_instrumentator.py` в корне репозитория предоставляет совместимую заглушку для экспорта метрик без отдельной установки пакета.

---

## Требования

- Docker 24+ и Docker Compose v2 (`docker compose`).
- Для Windows — запуск через WSL2.
- Не менее 4 ГБ RAM для контейнеров (Elasticsearch и ClickHouse требуют память).
- Для локальной разработки без Docker: Python 3.11+, Poetry/pip для установки зависимостей, Redis/PostgreSQL/Elasticsearch/ClickHouse при необходимости.

---

## Подготовка окружения

1. Клонируйте репозиторий и перейдите в корень.
2. Скопируйте пример файла окружения:
   ```bash
   cp .env.example .env
   ```
3. Обновите значения `.env` под свою среду (см. секцию ниже). Особое внимание — секретам и ключам профиля.
4. Убедитесь, что в `gateway/nginx.conf` у `proxy_pass` для `/api/auth/`, `/api/content/`, `/api/ugc/`, `/api/profile/` **нет завершающего слеша**.

### Ключевые переменные окружения

**Общие**
- `SERVER_NAME` — домен, который проксирует gateway (по умолчанию `localhost`).
- `JWT_SECRET`, `JWT_ALG` — общий секрет и алгоритм для Auth/Profile.

**PostgreSQL**
- `POSTGRES_USER`, `POSTGRES_PASSWORD` — учётные данные кластера.
- `POSTGRES_DB_AUTH`, `POSTGRES_DB_ADMIN` — имена баз, создаваемые для Auth и Django.
- `DATABASE_URL_PROFILES` — удобный DSN для профилей; сама база `profiles_db` создаётся вручную на этапе первого запуска.

**Auth service**
- `DATABASE_URL` — строка подключения SQLAlchemy (по умолчанию локальный SQLite `sqlite+aiosqlite:///./auth.db`).
- `ACCESS_TOKEN_EXPIRES_MIN`, `REFRESH_TOKEN_EXPIRES_MIN` — TTL токенов.
- Параметры логирования и наблюдаемости: `LOG_LEVEL`, `METRICS_ENABLED`, `TRACING_ENABLED`, `OTLP_ENDPOINT`, `SENTRY_DSN` и др.

**Content API**
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` и `REDIS_PASSWORD` — доступ к Redis.
- `ELASTIC_HOST`, `ELASTIC_PORT`, `ELASTIC_USERNAME`, `ELASTIC_PASSWORD` — доступ к Elasticsearch.
- `DEFAULT_PAGE_SIZE`, `CACHE_NAMESPACE`, `REDIS_CACHE_TTL_SECONDS` — параметры пагинации и кэша.
- Те же флаги наблюдаемости: `METRICS_ENABLED`, `TRACING_ENABLED`, `RATE_LIMIT_ENABLED` и т.п.

**Profile service**
- `DATABASE_URL` — DSN PostgreSQL (для локальной разработки допускается SQLite).
- `PROFILES_CRYPTO_KEY_BASE64` — 32-байтовый base64-ключ для AES-GCM.
- `PHONE_HASH_PEPPER` — pepper для хэширования телефонных номеров.
- `REDIS_HOST`, `REDIS_PORT` — кэш и SlowAPI rate limiting.
- Переключатели наблюдаемости и лимитов аналогичны другим сервисам.

**UGC service**
- Префикс окружения `UGC_`, вложенные параметры — через `__`.
  - Например: `UGC_CLICKHOUSE__HOST`, `UGC_CLICKHOUSE__PORT`, `UGC_CLICKHOUSE__USER`.
- `UGC_RATE_LIMIT_ENABLED`, `UGC_METRICS_ENABLED`, `UGC_TRACING_ENABLED` — функциональные флаги.

**Admin panel**
- `DJANGO_SECRET_KEY`, `DJANGO_SUPERUSER_*` — секрет Django и учётные данные суперпользователя.


### Генерация секретов профиля


Профильный сервис не стартует с заглушечным ключом — создайте новый:
```bash
python - <<'PY'
import base64, os
print(base64.b64encode(os.urandom(32)).decode())
PY
```
Полученное значение запишите в `PROFILES_CRYPTO_KEY_BASE64`. Pepper (`PHONE_HASH_PEPPER`) должен быть уникальным для окружения.

---

## Первый запуск

1. Запустите инфраструктурные сервисы:
   ```bash
   docker compose up -d db redis elasticsearch clickhouse
   ```
2. После того как health-checkи станут зелёными, создайте отдельные базы данных (при первом запуске):
   ```bash
   docker compose exec db psql -U ${POSTGRES_USER:-cinema} -c "CREATE DATABASE auth_db;"
   docker compose exec db psql -U ${POSTGRES_USER:-cinema} -c "CREATE DATABASE admin_db;"
   docker compose exec db psql -U ${POSTGRES_USER:-cinema} -c "CREATE DATABASE profiles_db;"
   docker compose exec db psql -U ${POSTGRES_USER:-cinema} -d admin_db -c "CREATE SCHEMA IF NOT EXISTS content AUTHORIZATION ${POSTGRES_USER:-cinema};"
   ```
3. Выполните миграции профилей (обязательный шаг перед запуском FastAPI-приложения):
   ```bash
   docker compose run --rm profile-service alembic upgrade head
   ```
4. (Опционально) убедитесь, что Django миграции проходят заранее:
   ```bash
   docker compose run --rm admin_panel python manage.py migrate
   ```
5. Соберите и поднимите весь стек:
   ```bash
   docker compose up -d --build
   # или
   make up
   ```
6. Просмотрите логи при первом старте:
   ```bash
   docker compose logs -f gateway
   ```

### Проверка готовности

Проверьте health-checkи через gateway:
```bash
curl http://localhost/health
curl http://localhost/api/auth/health
curl http://localhost/api/content/health
curl http://localhost/api/ugc/health
curl http://localhost/api/profile/health
```
* Для UGC сервис вернёт `{"status": "DEGRADED", "backend": "memory"}`, если ClickHouse недоступен и выбран встроенный in-memory репозиторий.
* Prometheus-метрики расположены по `/<svc>/metrics` (например, `http://localhost/api/auth/metrics`).

Админ-панель доступна по `http://localhost/admin/` (логин и пароль берутся из `.env`).

---

## Локальная разработка и качество


Установите инструменты качества:
```bash
make install-dev
```
Базовый рабочий цикл:
```bash
make format        # black
make lint          # ruff
make typecheck     # mypy
make check         # формат + линтеры + типы
```

Тесты запускаются отдельно для каждого сервиса:
```bash
pytest services/auth_service/tests
pytest services/content_api/tests
pytest services/profile_service/tests
pytest services/ugc_service/tests
```

### Частный запуск сервисов

Каждый сервис можно стартовать вне Docker, указав нужные переменные окружения:
```bash
# Auth service c SQLite (по умолчанию)
uvicorn services.auth_service.app.main:app --port 8001

# Profile service с локальной SQLite
DATABASE_URL=sqlite+aiosqlite:////tmp/profiles.db \
PROFILES_CRYPTO_KEY_BASE64=<ключ> \
PHONE_HASH_PEPPER=<pepper> \
uvicorn services.profile_service.app.main:app --port 8000

# Content API
ELASTIC_HOST=localhost REDIS_HOST=localhost \
uvicorn services.content_api.src.main:app --port 8002

```
`prometheus_fastapi_instrumentator.py` в корне обеспечивает доступность `/metrics`, даже если пакет отсутствует в окружении.

Тесты запускаются отдельно для каждого сервиса:
```bash
pytest services/auth_service/tests
pytest services/content_api/tests
pytest services/profile_service/tests
pytest services/ugc_service/tests
```

### Частный запуск сервисов

Каждый сервис можно стартовать вне Docker, указав нужные переменные окружения:
```bash
# Auth service c SQLite (по умолчанию)
uvicorn services.auth_service.app.main:app --port 8001

# Profile service с локальной SQLite
DATABASE_URL=sqlite+aiosqlite:////tmp/profiles.db \
PROFILES_CRYPTO_KEY_BASE64=<ключ> \
PHONE_HASH_PEPPER=<pepper> \
uvicorn services.profile_service.app.main:app --port 8000

# Content API
ELASTIC_HOST=localhost REDIS_HOST=localhost \
uvicorn services.content_api.src.main:app --port 8002
```
`prometheus_fastapi_instrumentator.py` в корне обеспечивает доступность `/metrics`, даже если пакет отсутствует в окружении.

---

## Наблюдаемость и эксплуатация


Все FastAPI-сервисы подключают общий middleware-пакет `services.common`:

- **Структурированные JSON-логи** c `request_id`, таймингами и заголовками (`REQUEST_LOG_HEADERS`).
- **Health-check** (`/health`) и **метрики Prometheus** (`/metrics`). Настраиваются через `*_METRICS_ENABLED`, `*_METRICS_ENDPOINT`.
- **OpenTelemetry**: включается переменными `*_TRACING_ENABLED`, `*_OTLP_ENDPOINT`, `*_TRACES_SAMPLE_RATIO`.
- **Sentry**: задайте `*_SENTRY_DSN`, `*_SENTRY_ENVIRONMENT`, `*_SENTRY_TRACES_SAMPLE_RATE`.
- **CORS и TrustedHost** управляются `*_CORS_*` и `*_ALLOWED_HOSTS`.
- **Rate limiting**: легковесный слайдинг-по-окну (`*_RATE_LIMIT_ENABLED`, `*_RATE_LIMIT_REQUESTS`, `*_RATE_LIMIT_WINDOW_SECONDS`). Профильный сервис дополнительно использует SlowAPI с Redis-хранилищем.

Gateway можно настроить на уровне Nginx (gzip, `proxy_next_upstream`, лимиты тела запроса) — смотрите `gateway/nginx.conf`.


Gateway можно настроить на уровне Nginx (gzip, `proxy_next_upstream`, лимиты тела запроса) — смотрите `gateway/nginx.conf`.

## API и документация


Swagger/OpenAPI доступен для каждого сервиса:
- Auth: `http://localhost/api/auth/openapi`
- Content: `http://localhost/api/content/openapi`
- Profile: `http://localhost/api/profile/openapi`
- UGC: `http://localhost/api/ugc/openapi`


Ключевые маршруты:

=======

**Auth**
- `POST /api/auth/register` — регистрация пользователя.
- `POST /api/auth/login` — выдача access/refresh токенов.
- `GET /api/auth/me` — данные текущего пользователя (Bearer JWT).


**Content**
- `GET /api/content/films` — список фильмов с пагинацией.
- `GET /api/content/films/{uuid}` — карточка фильма.
- Аналогичные маршруты для жанров и персон.


**Profile**
- `GET/POST/PUT/DELETE /api/profile` — CRUD профиля текущего пользователя.
- `GET/PUT /api/profile/me/ratings` — работа с персональными оценками.
- `GET /api/profile/public/films/{film_id}/rating-agg` — агрегированная оценка.
- `POST/DELETE/GET /api/profile/me/favorites` — избранное.

**UGC**
- `POST /api/ugc/event` — запись пользовательского события.
- `GET /api/ugc/events?limit=10` — чтение последних событий.

**Admin panel**
- Django admin с моделями фильмов/жанров/персон (схема `content`).

---

## Миграции и данные

- **Auth service** — при старте вызывает `Base.metadata.create_all`, поэтому схема создаётся автоматически; Alembic не используется.
- **Profile service** — миграции управляются Alembic (`services/profile_service/alembic.ini`). Создавайте новые файлы через `alembic revision --autogenerate -m "..."` и применяйте `alembic upgrade head`.
- **Admin panel** — миграции Django выполняются в `entrypoint.sh`, суперпользователь создаётся автоматически при наличии переменных окружения.
- **UGC** — при подключении к ClickHouse автоматически создаёт таблицу `events`. В деградированном режиме использует in-memory-хранилище.


---

## Типичные проблемы

| Симптом | Решение |
| ------- | ------- |
| Через gateway все API возвращают 404 | Убедитесь, что в `gateway/nginx.conf` у `proxy_pass` нет завершающего `/` — иначе Nginx удаляет префикс. Перезапустите gateway после правки. |
| Auth/Profile не стартуют из-за секретов | Проверьте `JWT_SECRET`, `PROFILES_CRYPTO_KEY_BASE64`, `PHONE_HASH_PEPPER`. Ключ профиля должен быть 32 байта (base64). |
| UGC возвращает `DEGRADED` | ClickHouse недоступен. Проверьте контейнер, логины, сеть. При восстановлении перезапустите UGC, чтобы вернуться к основному backend. |
| Elasticsearch/ClickHouse долго запускаются | Увеличьте лимит памяти Docker или дождитесь завершения health-checkов (30–90 секунд). |
| Порты 80/5432/6379/9200/8123 заняты | Освободите их или измените порт-маппинг в `docker-compose.yml`. |

---

## Дополнительные материалы

- [Спецификация профильного сервиса](PROFILE_SERVICE_SPEC.md)
- [Изменения по профилям](CHANGELOG.md)

