import httpx

from app.outreach.hostinger import HostingerMailError, choose_mailbox, get_mailboxes, send_message


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.is_success = 200 <= status_code < 300

    def json(self):
        return self._payload


def test_get_mailboxes_reads_scoped_mailboxes(monkeypatch):
    def fake_get(url, headers, timeout):
        assert url.endswith('/api/v1/me')
        assert headers['Authorization'] == 'Bearer secret'
        return FakeResponse(200, {'data': {'mailboxes': [
            {'resourceId': 'AC123', 'address': 'sales@example.com'},
            {'resourceId': 'AC456', 'address': 'hello@example.com'},
        ]}})
    monkeypatch.setattr(httpx, 'get', fake_get)
    result = get_mailboxes('secret')
    assert [mailbox.address for mailbox in result] == ['sales@example.com', 'hello@example.com']
    assert choose_mailbox(result, 'HELLO@example.com').resource_id == 'AC456'


def test_choose_mailbox_requires_selection_when_token_has_multiple():
    from app.outreach.hostinger import HostingerMailbox
    values = [HostingerMailbox('AC1', 'one@example.com'), HostingerMailbox('AC2', 'two@example.com')]
    try:
        choose_mailbox(values)
    except HostingerMailError as exc:
        assert 'multiple mailboxes' in str(exc)
    else:
        raise AssertionError('expected HostingerMailError')


def test_send_message_uses_hostinger_send_endpoint(monkeypatch):
    captured = {}
    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json)
        return FakeResponse(204)
    monkeypatch.setattr(httpx, 'post', fake_post)
    provider_id = send_message(
        api_token='token-value', mailbox_resource_id='AC123', to_email='lead@example.com',
        subject='Hello', body='Body text', display_name='Example Co',
    )
    assert captured['url'].endswith('/api/v1/mailboxes/AC123/send')
    assert captured['headers']['Authorization'] == 'Bearer token-value'
    assert captured['json']['to'] == ['lead@example.com']
    assert captured['json']['displayName'] == 'Example Co'
    assert provider_id == 'hostinger:AC123'


def test_invalid_token_returns_readable_error(monkeypatch):
    monkeypatch.setattr(httpx, 'get', lambda *args, **kwargs: FakeResponse(401, {'error': 'Unauthorized'}))
    try:
        get_mailboxes('bad-token')
    except HostingerMailError as exc:
        assert 'rejected this API token' in str(exc)
    else:
        raise AssertionError('expected HostingerMailError')
