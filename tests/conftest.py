import pytest
from aistent import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING': True, 'SECRET_KEY': 'test-session-key-with-at-least-32-characters', 'DATA_DIR': str(tmp_path), 'DATABASE': str(tmp_path / 'test.sqlite3'), 'STORAGE': str(tmp_path / 'files'), 'MAX_CONTENT_LENGTH': 256 * 1024, 'CSRF_DISABLED_FOR_TESTS': True})


@pytest.fixture
def client(app):
    client = app.test_client()
    assert client.post('/register', data={'email': 'owner@example.com', 'password': 'a-long-test-password'}).status_code == 302
    assert client.post('/login', data={'email': 'owner@example.com', 'password': 'a-long-test-password'}).status_code == 302
    return client


@pytest.fixture
def project_id(client):
    response = client.post('/projects', data={'title': 'Proiect test'})
    assert response.status_code == 302
    return int(response.headers['Location'].rsplit('/', 1)[1])
