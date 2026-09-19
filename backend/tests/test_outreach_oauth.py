import pytest
from app.outreach.oauth import make_state, verify_state, authorization_url


def test_oauth_state_round_trip():
    state = make_state("user-123", "secret-value")
    assert verify_state(state, "secret-value") == "user-123"


def test_oauth_state_rejects_wrong_secret():
    state = make_state("user-123", "secret-value")
    with pytest.raises(ValueError):
        verify_state(state, "wrong")


def test_authorization_url_requests_offline_gmail_send_scope():
    url = authorization_url(client_id="cid", redirect_uri="http://localhost/callback", state="abc")
    assert "access_type=offline" in url
    assert "gmail.send" in url
    assert "state=abc" in url
