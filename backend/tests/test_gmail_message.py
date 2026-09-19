import base64
from email import message_from_bytes
from app.outreach.gmail import build_raw_message


def test_build_raw_message_contains_expected_headers_and_body():
    raw = build_raw_message(sender_email="from@example.com", to_email="to@example.com", subject="Hello", body="Test body")
    decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    msg = message_from_bytes(decoded)
    assert msg["From"] == "from@example.com"
    assert msg["To"] == "to@example.com"
    assert msg["Subject"] == "Hello"
    assert "Test body" in decoded.decode()
