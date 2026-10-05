from app.db.models import ClaimStatus, DocumentStatus, PolicyStatus, UserRole


def test_postgres_enum_values_are_lowercase_values():
    assert UserRole.ADMIN.value == "admin"
    assert PolicyStatus.ACTIVE.value == "active"
    assert ClaimStatus.SUBMITTED.value == "submitted"
    assert DocumentStatus.ACTIVE.value == "active"
