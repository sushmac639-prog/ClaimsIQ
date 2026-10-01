from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.db.models import UserRole
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole
    region: str | None = Field(default=None, max_length=100)
class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    region: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    region: str | None
    is_active: bool
    created_at: datetime
