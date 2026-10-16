from app.api.routes.auth import logout
from app.schemas.auth import LogoutRequest


def test_logout_route_exists_and_accepts_optional_refresh_token():
    assert callable(logout)
    assert LogoutRequest().refresh_token is None
    assert LogoutRequest(refresh_token="sample").refresh_token == "sample"
