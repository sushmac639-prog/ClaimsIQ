from pathlib import Path


def test_initial_migration_creates_each_postgres_enum_once():
    migration_text = Path("migrations/versions/0001_initial.py").read_text()
    assert migration_text.count("user_role.create") == 1
    assert migration_text.count("policy_status.create") == 1
    assert migration_text.count("claim_status.create") == 1
    assert migration_text.count("history_old.create") == 1
    assert migration_text.count("history_new.create") == 1
