from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import ClaimStatus
class ClaimCreate(BaseModel):
    claim_number: str = Field(min_length=3, max_length=80)
    policy_id: int
    assigned_user_id: int | None = None
    claimant_name: str = Field(min_length=2, max_length=150)
    claim_type: str = Field(min_length=2, max_length=80)
    claim_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    region: str = Field(min_length=2, max_length=100)
class ClaimUpdate(BaseModel):
    assigned_user_id: int | None = None
    claimant_name: str | None = Field(default=None, min_length=2, max_length=150)
    claim_type: str | None = Field(default=None, min_length=2, max_length=80)
    claim_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    region: str | None = Field(default=None, min_length=2, max_length=100)
class ClaimStatusUpdate(BaseModel):
    new_status: ClaimStatus
    justification: str | None = Field(default=None, max_length=2000)
class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    claim_number: str
    policy_id: int
    assigned_user_id: int | None
    claimant_name: str
    claim_type: str
    claim_amount: Decimal
    region: str
    status: ClaimStatus
    submitted_at: datetime
    closed_at: datetime | None
class NoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    claim_id: int
    created_by: int
    note: str
    created_at: datetime
