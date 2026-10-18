"""Contracte API simulate: niciun test nu apelează un model plătit."""
import base64
import json
from io import BytesIO

import pytest
from PIL import Image
import requests

from aistent import ai, video_ai
from aistent.db import db
from test_workspace import upload


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('AISTENT_AI_KEY', 'fake-test-key-not-a-secret')
    monkeypatch.setenv('AISTENT_VIDEO_KEY', 'fake-video-key-not-a-secret')
    for action in ai.ACTIONS:
        monkeypatch.setenv('AISTENT_COST_' + action.upper() + '_USD', '0.05')
    for operation in ('GENERATE', 'EDIT'):
        monkeypatch.setenv('AISTENT_VIDEO_' + operation + '_VERSION', 'a' * 64)
        template = {'prompt': '$PROMPT', 'duration': 4}
        template['video' if operation == 'EDIT' else 'image'] = '$VIDEO' if operation == 'EDIT' else '$IMAGE'
        monkeypatch.setenv('AISTENT_VIDEO_' + operation + '_INPUT', json.dumps(template))


def new_quote(client, project_id, action='chat', **extra):
    response = client.post(f'/projects/{project_id}/quote', data={'action': action, 'prompt': 'Explică în română', **extra})
    assert response.status_code == 302
    return response.headers['Location']


def test_ai_unconfigured_is_disabled(client, project_id, monkeypatch):
    monkeypatch.delenv('AISTENT_AI_KEY', raising=False)
    response = client.post(f'/projects/{project_id}/quote', data={'prompt': 'Salut', 'action': 'chat'})
    assert response.status_code == 400
    assert 'Configurează' in response.text


def test_quote_confirmation_single_use_and_history(client, project_id, configured, monkeypatch):
    calls = []
    def respond(action, payload, records, history):
        calls.append(payload)
        return {'text': 'Răspuns în română', 'sources': [{'title': 'Sursă', 'url': 'https://example.org'}]}
    monkeypatch.setattr(ai, 'text_result', respond)
    location = new_quote(client, project_id)
    assert calls == []  # Merely estimating must never charge.
    page = client.get(location)
    assert page.status_code == 200 and '0.0500' in page.text
    assert client.post(location + '/confirm').status_code == 400
    assert not calls
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 302
    assert len(calls) == 1
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 400
    assert len(calls) == 1
    page = client.get(f'/projects/{project_id}')
    assert 'Răspuns în română' in page.text and 'https://example.org' in page.text


def test_quote_other_owner_and_expiry(app, client, project_id, configured, monkeypatch):
    monkeypatch.setattr(ai, 'text_result', lambda *args: pytest.fail('Must not call paid API'))
    location = new_quote(client, project_id)
    other = app.test_client()
    other.post('/register', data={'email': 'other@example.com', 'password': 'a-long-other-password'})
    other.post('/login', data={'email': 'other@example.com', 'password': 'a-long-other-password'})
    assert other.get(location).status_code == 404
    assert other.post(location + '/confirm', data={'consent': 'yes'}).status_code == 404
    with app.app_context():
        db().execute("UPDATE quotes SET created=datetime('now','-20 minutes')")
        db().commit()
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 400


def test_changed_cost_or_model_requires_new_quote(client, project_id, configured, monkeypatch):
    location = new_quote(client, project_id)
    monkeypatch.setenv('AISTENT_COST_CHAT_USD', '0.10')
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 400


def test_failed_charge_not_retried(client, project_id, configured, monkeypatch):
    calls = []
    def failure(*args):
        calls.append(True)
        raise ValueError('Timeout; verifică facturarea')
    monkeypatch.setattr(ai, 'text_result', failure)
    location = new_quote(client, project_id)
    for _ in range(2):
        assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 400
    assert len(calls) == 1


def test_responses_contract_sources_and_selected_files(client, project_id, configured, monkeypatch):
    file_id = upload(client, project_id, 'date.txt', 'Date personale selectate'.encode())
    calls = []
    class Response:
        def json(self):
            return {'output': [{'content': [{'type': 'output_text', 'text': 'Rezultat', 'annotations': [{'type': 'url_citation', 'title': 'Documentație', 'url': 'https://example.org/doc'}, {'type': 'url_citation', 'url': 'javascript:alert(1)'}]}]}]}
    def api_call(method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs))
        return Response()
    monkeypatch.setattr(ai, 'api', api_call)
    location = new_quote(client, project_id, 'search', file_ids=file_id)
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 302
    method, endpoint, kwargs = calls[0]
    assert method == 'POST' and endpoint == 'responses'
    body = kwargs['json']
    assert body['tools'][0]['type'] == 'web_search'
    assert body['max_tool_calls'] == 1
    assert any('Date personale selectate' in item.get('text', '') for item in body['input'][-1]['content'])
    with client.application.app_context():
        sources = json.loads(db().execute("SELECT sources FROM messages WHERE role='assistant'").fetchone()[0])
        assert len(sources) == 1 and sources[0]['url'].startswith('https://')


def test_image_api_contract_and_private_output(client, project_id, configured, monkeypatch):
    image = BytesIO()
    Image.new('RGB', (16, 16), 'blue').save(image, 'PNG')
    class Response:
        def json(self):
            return {'data': [{'b64_json': base64.b64encode(image.getvalue()).decode()}]}
    calls = []
    def api_call(method, endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return Response()
    monkeypatch.setattr(ai, 'api', api_call)
    source = upload(client, project_id, 'source.png', image.getvalue())
    for action in ('image_generate', 'image_edit'):
        location = new_quote(client, project_id, action, **({'file_ids': source} if action == 'image_edit' else {}))
        assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 302
    assert calls[0][0] == 'images/generations'
    assert calls[1][0] == 'images/edits'
    assert 'files' in calls[1][1]
    with client.application.app_context():
        assert db().execute("SELECT COUNT(*) FROM files WHERE name='imagine-ai.png'").fetchone()[0] == 2


def test_video_create_poll_and_download(client, project_id, configured, monkeypatch):
    calls = []
    def create(action, payload, records):
        calls.append(action)
        assert payload['video_config']['version'] == 'a' * 64
        return {'id': 'prediction123', 'status': 'starting'}
    monkeypatch.setattr(video_ai, 'create', create)
    monkeypatch.setattr(video_ai, 'status', lambda identifier: {'status': 'succeeded', 'output': 'https://replicate.delivery/test.mp4'})
    monkeypatch.setattr(video_ai, 'download', lambda result: b'test-video-output')
    location = new_quote(client, project_id, 'video_generate')
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 302
    assert client.post(location + '/poll').status_code == 302
    assert client.post(location + '/poll').status_code == 400
    assert calls == ['video_generate']
    with client.application.app_context():
        row = db().execute("SELECT * FROM files WHERE name='video-ai.mp4'").fetchone()
        assert row is not None
    assert client.get(f"/files/{row['id']}").data == b'test-video-output'


def test_video_input_mapping(configured, monkeypatch, app, client, project_id):
    captured = []
    def api_call(method, path, **kwargs):
        captured.append((path, kwargs))
        if path == 'files':
            return {'urls': {'get': 'https://api.replicate.com/v1/files/file123'}}
        return {'id': 'prediction123'}
    monkeypatch.setattr(video_ai, 'api', api_call)
    output = BytesIO()
    Image.new('RGB', (16, 16)).save(output, 'PNG')
    file_id = upload(client, project_id, 'image.png', output.getvalue())
    location = new_quote(client, project_id, 'video_generate', file_ids=file_id)
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 302
    body = captured[-1][1]['json']
    assert body['input']['prompt'] == 'Explică în română'
    assert body['input']['image'] == 'https://api.replicate.com/v1/files/file123'
    assert body['input']['duration'] == 4


def test_video_download_blocks_arbitrary_urls(monkeypatch):
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: pytest.fail('Must not fetch untrusted URL'))
    for url in ('http://127.0.0.1/x', 'https://example.org/x', 'https://replicate.delivery.evil.test/x', 'https://user:pass@replicate.delivery/x'):
        with pytest.raises(ValueError):
            video_ai.download({'output': url})


def test_ai_api_never_retries_or_disables_tls(configured, monkeypatch):
    calls = []
    def fail(*args, **kwargs):
        calls.append(kwargs)
        assert kwargs.get('verify', True) is True
        raise requests.Timeout()
    monkeypatch.setattr(requests, 'request', fail)
    with pytest.raises(ValueError, match='facturării'):
        ai.api('POST', 'responses', json={})
    assert len(calls) == 1


def test_estimated_daily_budget_blocks_paid_call(app, client, project_id, configured, monkeypatch):
    app.config['AI_DAILY_USER_ESTIMATE_USD'] = 0.01
    monkeypatch.setattr(ai, 'text_result', lambda *args: pytest.fail('Budget must prevent paid call'))
    location = new_quote(client, project_id)
    response = client.post(location + '/confirm', data={'consent': 'yes'})
    assert response.status_code == 400
    assert 'Limita zilnică' in response.text


def test_video_template_change_requires_reconfirmation(client, project_id, configured, monkeypatch):
    location = new_quote(client, project_id, 'video_generate')
    monkeypatch.setenv('AISTENT_VIDEO_GENERATE_INPUT', '{"prompt":"$PROMPT","duration":8}')
    assert client.post(location + '/confirm', data={'consent': 'yes'}).status_code == 400
