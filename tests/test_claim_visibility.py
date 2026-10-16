from sqlalchemy.dialects import postgresql

from app.api.routes.claims import visible_claims_stmt
from app.api.routes.policies import visible_policies_stmt
from app.db.models import User, UserRole


def sql_for(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_support_agent_claim_query_is_region_scoped():
    user = User(id=12, role=UserRole.SUPPORT_AGENT, region="South")
    sql = sql_for(visible_claims_stmt(user))
    assert "lower(claims.region) = 'south'" in sql
    assert "claims.archived_at IS NULL" in sql


def test_adjuster_claim_query_is_limited_to_assignment_or_region():
    user = User(id=12, role=UserRole.CLAIMS_ADJUSTER, region="South")
    sql = sql_for(visible_claims_stmt(user))
    assert "claims.assigned_user_id = 12" in sql
    assert "lower(claims.region) = 'south'" in sql


def test_manager_claim_query_is_not_restricted_to_one_region():
    user = User(id=1, role=UserRole.CLAIMS_MANAGER, region="South")
    sql = sql_for(visible_claims_stmt(user))
    assert "lower(claims.region) = 'south'" not in sql
    assert "claims.archived_at IS NULL" in sql


def test_support_agent_policy_query_is_region_scoped():
    user = User(id=12, role=UserRole.SUPPORT_AGENT, region="South")
    sql = sql_for(visible_policies_stmt(user))
    assert "lower(policies.region) = 'south'" in sql
    assert "lower(policies.region) = 'global'" in sql
