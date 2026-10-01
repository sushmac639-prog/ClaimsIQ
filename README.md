# ClaimIQ

ClaimIQ is a FastAPI-based insurance claims and policy management platform with PostgreSQL, SQLAlchemy 2.0, Alembic migrations, JWT authentication, Argon2 password hashing, role-based access control, policy and claim CRUD APIs, claim notes, workflow validation, and audit logging.

## Technology stack

- Python 3.11+
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0
- Alembic
- PyJWT
- pwdlib + Argon2
- Docker / Docker Compose
- pytest

## Project structure

```text
claimiq/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── claims.py
│   │       ├── health.py
│   │       ├── policies.py
│   │       └── users.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── claim.py
│   │   ├── policy.py
│   │   └── user.py
│   └── main.py
├── migrations/
│   ├── versions/0001_initial.py
│   └── env.py
├── scripts/seed_admin.py
├── tests/test_health.py
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Run with Docker

1. Copy `.env.example` to `.env`.
2. Replace `JWT_SECRET_KEY` with a strong random value.
3. Run:

```bash
docker compose up --build
```

4. In another terminal:

```bash
docker compose exec api python scripts/seed_admin.py
```

5. Open Swagger UI:

`http://localhost:8000/docs`

## Run locally with Docker PostgreSQL

```bash
docker compose up -d db
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python scripts/seed_admin.py
uvicorn app.main:app --reload
```

## API endpoints

- `GET /` - root check
- `GET /api/v1/health` - database health
- `POST /api/v1/auth/login` - OAuth2 form login
- `POST /api/v1/auth/refresh` - refresh JWT pair
- `GET /api/v1/auth/me` - current profile
- `/api/v1/users` - Admin user administration
- `/api/v1/policies` - policy CRUD
- `/api/v1/claims` - claim CRUD, notes and status workflow

## Claim workflow

`submitted -> under_review -> approved/rejected -> closed`

Admins and Claims Managers can override the normal transition when a justification is supplied.

## Tests

```bash
pytest -q
```

## Migrations

After changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe the model change"
alembic upgrade head
alembic current
```

Always review generated migrations before applying them.

## Security notes

Do not commit `.env` or real credentials. For production, use HTTPS, managed secrets, refresh-token revocation/rotation, rate limiting, centralized logging, backup/restore testing, and a security review.
