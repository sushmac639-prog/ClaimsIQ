from app.core.security import create_access_token, create_refresh_token, decode_token


def test_access_token_has_jti_and_access_type():
    token = create_access_token("42")
    payload = decode_token(token, "access")
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_refresh_token_has_refresh_type():
    token = create_refresh_token("42")
    payload = decode_token(token, "refresh")
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"
    assert payload["jti"]
