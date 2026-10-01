from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models import PolicyStatus
class PolicyCreate(BaseModel):
    policy_number: str = Field(min_length=3, max_length=80)
    policy_type: str = Field(min_length=2, max_length=80)
    coverage_description: str | None = None
    region: str = Field(min_length=2, max_length=100)
    effective_date: date
    expiry_date: date
    status: PolicyStatus = PolicyStatus.ACTIVE
    @model_validator(mode="after")
    def validate_dates(self):
        if self.expiry_date <= self.effective_date:
            raise ValueError("expiry_date must be after effective_date")
        return self
class PolicyUpdate(BaseModel):
    policy_type: str | None = Field(default=None, min_length=2, max_length=80)
    coverage_description: str | None = None
    region: str | None = Field(default=None, min_length=2, max_length=100)
    effective_date: date | None = None
    expiry_date: date | None = None
    status: PolicyStatus | None = None
class PolicyRead(PolicyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
