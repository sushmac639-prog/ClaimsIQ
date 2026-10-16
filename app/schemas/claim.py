from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import ClaimStatus


class ClaimCreate(BaseModel):
    claim_number: str = Field(min_length=3, max_length=80)
    policy_id: int = Field(ge=1)
    assigned_user_id: int | None = Field(default=None, ge=1)
    claimant_name: str = Field(min_length=2, max_length=150)
    claim_type: str = Field(min_length=2, max_length=80)
    claim_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    region: str = Field(min_length=2, max_length=100)

    @field_validator("claim_number", "claimant_name", "claim_type", "region")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class ClaimUpdate(BaseModel):
    assigned_user_id: int | None = Field(default=None, ge=1)
    claimant_name: str | None = Field(default=None, min_length=2, max_length=150)
    claim_type: str | None = Field(default=None, min_length=2, max_length=80)
    claim_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    region: str | None = Field(default=None, min_length=2, max_length=100)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self):
        for field in ("claimant_name", "claim_type", "claim_amount", "region"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

    @field_validator("claimant_name", "claim_type", "region")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class ClaimStatusUpdate(BaseModel):
    new_status: ClaimStatus
    justification: str | None = Field(default=None, max_length=2000)

    @field_validator("justification")
    @classmethod
    def strip_justification(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


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
    archived_at: datetime | None = None


class NoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=2000)

    @field_validator("note")
    @classmethod
    def note_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Note must not be blank")
        return value


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    claim_id: int
    created_by: int
    note: str
    created_at: datetime
