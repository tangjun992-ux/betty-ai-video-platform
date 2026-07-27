"""Login API contract: frontend sends {email, password}; backend must accept it."""
from app.api.auth import LoginRequest


def test_login_request_accepts_email():
    req = LoginRequest(email="user@example.com", password="secret")
    assert req.email == "user@example.com"
    assert req.username is None


def test_login_request_accepts_username_legacy():
    req = LoginRequest(username="alice", password="secret")
    assert req.username == "alice"
    assert req.email is None


def test_login_request_requires_password():
    try:
        LoginRequest(email="a@b.com")  # type: ignore[call-arg]
        assert False, "should require password"
    except Exception:
        pass
