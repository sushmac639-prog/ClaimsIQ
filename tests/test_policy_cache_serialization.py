from datetime import date, datetime, timezone

from app.db.models import Policy, PolicyStatus
from app.schemas.policy import PolicyRead


def test_policy_orm_row_can_be_serialized_for_redis_cache():
    now = datetime.now(timezone.utc)
    policy = Policy(
        id=2,
        policy_number="2",
        policy_type="health",
        coverage_description="Hospitalization coverage",
        region="South",
        effective_date=date(2026, 1, 1),
        expiry_date=date(2027, 1, 1),
        status=PolicyStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    payload = PolicyRead.model_validate(policy).model_dump(mode="json")

    assert payload["id"] == 2
    assert payload["policy_number"] == "2"
    assert payload["status"] == "active"
