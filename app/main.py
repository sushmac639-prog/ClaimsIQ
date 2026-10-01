from fastapi import FastAPI
from app.api.routes import auth, claims, health, policies, users
from app.core.config import settings

tags_metadata = [
    {"name":"Authentication","description":"Login, refresh, and current-user operations."},
    {"name":"Users","description":"Admin-only user lifecycle operations."},
    {"name":"Policies","description":"Policy management and lookup."},
    {"name":"Claims","description":"Claims, notes, and status workflow."},
    {"name":"Health","description":"API and database connectivity checks."},
]
app = FastAPI(title=settings.app_name, description="Insurance claims and policy management platform", version="1.0.0", openapi_tags=tags_metadata)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
@app.get("/")
def root() -> dict[str, str]:
    return {"message":"ClaimIQ API is running"}
