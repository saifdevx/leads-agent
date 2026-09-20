from app.outreach import sending


class Repo:
    def get_sender(self, user_id, sender_id, with_credentials=False):
        assert with_credentials is True
        return {
            "id": sender_id,
            "provider": "hostinger",
            "email": "hello@example.com",
            "display_name": "Example",
            "credentials": {"api_token": "secret", "mailbox_resource_id": "box-1"},
        }


def test_send_with_sender_uses_hostinger(monkeypatch):
    called = {}

    def fake_send(**kwargs):
        called.update(kwargs)
        return "hostinger:box-1"

    monkeypatch.setattr(sending, "send_hostinger_message", fake_send)
    provider_id = sending.send_with_sender(
        Repo(), user_id="user-1", sender_id="sender-1",
        to_email="person@example.com", subject="Hello", body="Body",
    )
    assert provider_id == "hostinger:box-1"
    assert called["to_email"] == "person@example.com"
    assert called["mailbox_resource_id"] == "box-1"
