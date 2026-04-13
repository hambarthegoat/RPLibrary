# RPLibrary API (Simple Clean Architecture)

API sederhana untuk manajemen perpustakaan Lab RPL, dengan:
- register & login JWT
- role admin vs user
- CRUD buku + upload cover
- upload avatar user
- peminjaman + request return + konfirmasi return admin
- CRUD tag + search/filter buku

## Stack

- **FastAPI**: dedicated, docs otomatis (`/docs`, `/redoc`). Atatu di /docs untuk hoppscotch docs.
- **SQLAlchemy ORM**: model dan query.
- **PostgreSQL**: relational database.
- **Alembic**: versioning skema database (migrasi).
- **JWT + bcrypt**: autentikasi stateless dengan password hash aman.
- **uv**: dependency/project runner yang ringan dan cepat.

## Struktur project

```text
app/
  core/             # config, security
  infrastructure/   # engine/session + SQLAlchemy models
  application/      # schemas + business services
  presentation/     # FastAPI routes + auth dependencies
alembic/
  versions/         # migration scripts
main.py             # entrypoint app
```

## Setup

1. Install dependency:
   ```bash
   uv sync
   ```
2. Siapkan env:
   ```bash
   cp .env.example .env
   ```
3. Isi `.env` (utama: `DATABASE_URL` PostgreSQL).
4. Jalankan migrasi:
   ```bash
   uv run alembic upgrade head
   ```
5. Jalankan API:
   ```bash
   uv run uvicorn main:app --reload
   ```

## Hoppscotch 
- `its.id/m/RPLibrary`  
