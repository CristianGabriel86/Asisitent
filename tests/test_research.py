import requests
from aistent import research
from aistent.db import db


def test_crossref_metadata_saved_with_real_doi(client, project_id, monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'message': {'items': [{'title': ['Articol de test'], 'DOI': '10.1234/example', 'author': [{'given': 'Ana', 'family': 'Pop'}], 'published': {'date-parts': [[2024]]}}]}}
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: Response())
    response = client.post(f'/projects/{project_id}/bibliography', data={'query': 'electrical installations'})
    assert response.status_code == 302
    with client.application.app_context():
        text = db().execute('SELECT content FROM messages').fetchone()[0]
        assert 'Ana Pop (2024)' in text and 'https://doi.org/10.1234/example' in text
    assert 'Articol de test' in client.get(f'/projects/{project_id}').text


def test_crossref_outage_does_not_invent_references(client, project_id, monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(requests, 'get', fail)
    assert client.post(f'/projects/{project_id}/bibliography', data={'query': 'electric'}).status_code == 400
    with client.application.app_context():
        assert db().execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 0
