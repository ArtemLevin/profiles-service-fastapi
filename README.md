# Profile Service — Online Cinema

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.x-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7%2B-DC382D?logo=redis)
![OpenAPI 3](https://img.shields.io/badge/OpenAPI-3.0-6BA539?logo=openapiinitiative)
![Status](https://img.shields.io/badge/status-WIP-orange)
![License](https://img.shields.io/badge/License-TBD-lightgrey)

> A FastAPI microservice for managing user **profiles**, **favorites**, **ratings**, and **reviews** for an Online Cinema platform — with strong guarantees for PII security, auditability, and performance.

**Repository (develop branch):** https://github.com/ArtemLevin/graduate_work/tree/develop

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [API (Draft)](#api-draft)
- [Data Model (Sketch)](#data-model-sketch)
- [Security & Compliance](#security--compliance)
- [Performance & Reliability](#performance--reliability)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
  - [Run Locally](#run-locally)
  - [Example with Docker Compose](#example-with-docker-compose)
- [Observability](#observability)
- [Admin Access](#admin-access)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

**Profile Service** is a standalone service within the *Online Cinema* monorepo that owns:

- User **profiles** (PII)
- **Favorites**: add/remove movies to a personal list
- **Ratings**: 1..10 (0.5 steps), with public aggregates (avg/count)
- **Reviews**: CRUD for personal reviews with moderation
- Public **aggregates** and listings exposed to other services

The service integrates with **Auth Service** via JWT, **Content API** for public aggregates, and an **Admin Panel** for secure PII access.

---

## Features

- **Profile CRUD**: one active profile per `user_id`; unique phone numbers
- **Favorites**: idempotent add/remove; pagination & sort by creation
- **Ratings**: idempotent upsert; `avg_rating`/`ratings_count` cached in Redis
- **Reviews**: one review per (user, film); statuses `published|hidden|moderation`
- **Public endpoints** for aggregates & recent reviews (no PII leakage)
- **Admin endpoints** gated by role (e.g., `profiles.view_sensitive`)
- **Audit logging** of PII access and profile changes

---

## Architecture

Stack: **FastAPI** (HTTP), **PostgreSQL** (primary data store), **Redis** (caching), optional **Django Admin** for back-office.

### Component Diagram (service in context)

```mermaid
flowchart LR
  subgraph Client
    U[User]
    A[Administrator]
  end

  U -->|JWT| GW[Gateway (Nginx)];;
  A -->|JWT| GW;;

  GW --> PS[Profile Service (FastAPI)];;
  GW --> CA[Content API];;
  GW --> AS[Auth Service];;
  A --> DJ[Admin Panel (Django)];;

  PS -->|SQL| PG[PostgreSQL: profiles_db];;
  PS -->|cache| RD[Redis];;
  CA --> ES[Elasticsearch];;
  UGC[UGC Service] --> CH[ClickHouse];;

  CA <--> PS;;
  DJ <--> PS;;
  AS <--> PS;;


```

### Class Diagram (core domain)

```mermaid
classDiagram
  class Profile {
    +uuid id
    +uuid user_id
    +string full_name
    +string phone_e164_enc
    +string phone_hash
    +bool marketing_opt_in
    +bool twofa_phone_verified
    +datetime created_at
    +datetime updated_at
  }

  class Favorite {
    +uuid id
    +uuid profile_id
    +uuid film_id
    +datetime created_at
  }

  class Rating {
    +uuid id
    +uuid profile_id
    +uuid film_id
    +decimal rating 1..10
    +datetime updated_at
  }

  class Review {
    +uuid id
    +uuid profile_id
    +uuid film_id
    +string title
    +text body
    +decimal rating 1..10
    +enum status [published|hidden|moderation]
    +datetime created_at
    +datetime updated_at
  }

  class AuditLog {
    +uuid id
    +uuid actor_user_id
    +string action
    +uuid target_profile_id
    +json fields_masked
    +datetime created_at
  }

  Profile "1" <-- "0..*" Favorite : has
  Profile "1" <-- "0..*" Rating : has
  Profile "1" <-- "0..*" Review : has
```

---

## API (Draft)

**Auth**: Use Bearer JWT for all private endpoints.

### Profile
- `GET /api/profile/me` → `200 {profile}`
- `POST /api/profile` `{full_name, phone}` → `201 {profile}`
- `PUT /api/profile` `{full_name?, phone?, marketing_opt_in?}` → `200 {profile}`
- `DELETE /api/profile` → `204`

### Favorites
- `GET /api/profile/me/favorites?limit&offset` → `200 {items:[{film_id,added_at}], total}`
- `POST /api/profile/me/favorites` `{film_id}` → `200/201`
- `DELETE /api/profile/me/favorites/{film_id}` → `204`

### Ratings
- `GET /api/profile/me/ratings?film_id?` → `200`
- `PUT /api/profile/me/ratings` `{film_id, rating}` → `200 {rating}`
- `GET /api/profile/public/films/{film_id}/rating-agg` → `200 {avg_rating, ratings_count}`

### Reviews
- `GET /api/profile/public/films/{film_id}/reviews?limit&offset&sort=recent|top` → `200`
- `POST /api/profile/me/reviews` `{film_id, title?, body, rating?}` → `201`
- `PUT /api/profile/me/reviews/{film_id}` → `200`
- `DELETE /api/profile/me/reviews/{film_id}` → `204`
- **Admin:** `PUT /api/profile/admin/reviews/{id}/status` `{status}`

### Admin (PII)
- `GET /api/profile/admin/search?phone=...` — search by `phone_hash`
- `GET /api/profile/admin/{user_id}` — full profile view (sensitive; role-restricted)

### Sequence (rating upsert)
```mermaid
sequenceDiagram
  participant User
  participant Gateway as Nginx
  participant ProfileAPI as Profile Service
  participant Redis
  participant Postgres as Postgres (profiles_db)
  participant Auth as Auth Service

  User->>Gateway: PUT /api/profile/me/ratings {film_id, rating} (Bearer JWT)
  Gateway->>Auth: /api/auth/me (validate JWT)
  Auth-->>Gateway: 200 {user_id}
  Gateway->>ProfileAPI: PUT /ratings (user_id, film_id, rating)

  ProfileAPI->>Postgres: UPSERT Rating(profile_id, film_id, rating)
  Postgres-->>ProfileAPI: OK
  ProfileAPI->>Postgres: SELECT AVG, COUNT FROM ratings WHERE film_id=...
  Postgres-->>ProfileAPI: {avg, count}
  ProfileAPI->>Redis: SET film:{id}:rating_agg {avg,count} TTL=300
  ProfileAPI-->>Gateway: 200 {rating, agg:{avg,count}}
  Gateway-->>User: 200 OK
```

---

## Data Model (Sketch)

```sql
create table profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique,
  full_name text not null,
  phone_e164_enc bytea not null,        -- ciphertext (AES-256-GCM / pgcrypto AES)
  phone_hash bytea not null unique,     -- sha256(pepper + e164)
  marketing_opt_in boolean default false,
  twofa_phone_verified boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table favorites (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles(id) on delete cascade,
  film_id uuid not null,
  created_at timestamptz default now(),
  unique(profile_id, film_id)
);

create table ratings (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles(id) on delete cascade,
  film_id uuid not null,
  rating numeric(3,1) not null check (rating >= 1 and rating <= 10 and rating*2 = floor(rating*2)),
  updated_at timestamptz default now(),
  unique(profile_id, film_id)
);

create table reviews (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles(id) on delete cascade,
  film_id uuid not null,
  title text,
  body text not null,
  rating numeric(3,1),
  status text not null default 'published' check (status in ('published','hidden','moderation')),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(profile_id, film_id)
);

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid not null,
  action text not null,
  target_profile_id uuid not null,
  fields_masked jsonb not null,
  created_at timestamptz default now()
);
```

---

## Security & Compliance

- **PII Protection**
  - `phone_e164_enc` encrypted at application layer (AES‑256‑GCM) or via `pgcrypto` in Postgres.
  - `phone_hash` (SHA‑256 + pepper) stored & indexed; unique constraint enforces uniqueness.
- **AuthN/Z**: JWT for all private endpoints; RBAC with least privilege.
- **Rate limiting**: baseline 60 rps / user, 10 rps / IP for public endpoints.
- **Audit logging** for any access to PII; PII is masked in logs.
- **Backups**: daily; retention ≥ 30 days; encrypted at rest.
- **Data subject rights**: export & deletion (soft delete + hard delete on request).
- **Secrets**: keys in a Secret Manager or environment variables (never in git).

---

## Performance & Reliability

- **Availability (prod)**: 99.9%
- **Latency targets**: p95 < 100–150 ms for CRUD; aggregates < 200 ms (cache hit < 50 ms)
- **Horizontal scaling**: stateless HTTP; no sticky sessions
- **Idempotency**: for favorites add and rating upsert
- **Caching**: film rating aggregates in Redis (TTL ≈ 5 min)

---

## Getting Started

### Prerequisites
- Python **3.11+**
- PostgreSQL **14+**
- Redis **7+**
- (Optional) Poetry or uv/pip-tools
- OpenSSL (for generating encryption keys)

### Configuration

Create a `.env` (or export as env vars):

```bash
# Database
PROFILE_DB_DSN=postgresql+psycopg2://user:pass@localhost:5432/profiles_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_PUBLIC_KEY_PATH=./secrets/jwt_pub.pem

# PII encryption (32-byte key for AES-256-GCM; base64-encoded)
PII_ENC_KEY_B64=YOUR_BASE64_KEY_HERE

# Rate limits (sane defaults)
RATE_LIMIT_PER_USER=60
RATE_LIMIT_PER_IP_PUBLIC=10
```

> **Note:** do not commit real secrets. Use a secrets manager in production.

### Run Locally

```bash
# 1) Create a virtual environment & install deps
python -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
# If using Poetry:
#   pip install poetry && poetry install

# 2) Migrations (Alembic)
# alembic upgrade head

# 3) Start the service
uvicorn app.main:app --reload --port 8080

# 4) OpenAPI (Swagger UI)
# http://localhost:8080/docs
```

### Example with Docker Compose

> Minimal example — adapt image/build context and secrets to your repository layout.

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: profiles_db
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports: ["6379:6379"]

  profile-service:
    build: .
    depends_on: [postgres, redis]
    environment:
      PROFILE_DB_DSN: postgresql+psycopg2://app:app@postgres:5432/profiles_db
      REDIS_URL: redis://redis:6379/0
      JWT_PUBLIC_KEY_PATH: /run/secrets/jwt_pub
      PII_ENC_KEY_B64: ${PII_ENC_KEY_B64:?set_me}
    ports: ["8080:8080"]
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8080"
    secrets:
      - jwt_pub

secrets:
  jwt_pub:
    file: ./secrets/jwt_pub.pem

volumes:
  pgdata: {}
```

---

## Observability

- **Metrics**: Prometheus endpoints; RED/Golden signals for HTTP
- **Tracing**: OpenTelemetry integration (propagation from Gateway)
- **Structured logs**: JSON format with request IDs and masked PII

---

## Admin Access

A Django-based Admin Panel (or admin APIs) provides controlled access to PII for users with dedicated roles (e.g., `profiles.view_sensitive`). Admin endpoints and queries operate on a read-only basis unless explicitly permitted.

---

## Roadmap

- Postman collection & OpenAPI examples
- Bulk export & deletion flows
- Review moderation UI
- Async eventing for recommendations
- ES/analytics replication of aggregates

---

## Contributing

- Style: `black`, `ruff`
- Tests: unit + integration (DB/Redis); run in CI
- Commits: Conventional Commits recommended
- PRs: include test coverage and update docs where relevant

---

## License

**TBD** — choose a license that matches your distribution model (e.g., MIT/Apache-2.0 for open-source, or a private license for internal use).

---

## Acknowledgements

- Built with **FastAPI**, **SQLAlchemy**, **Alembic**, **PostgreSQL**, **Redis**
- Thanks to contributors and reviewers of the Online Cinema monorepo

---

> **See also:** the detailed service specification in `PROFILE_SERVICE_SPEC.md`.
