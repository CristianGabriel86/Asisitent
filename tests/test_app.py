from io import BytesIO

from docx import Document
from aistent import create_app


def test_home():
    response = create_app().test_client().get('/')
    assert response.status_code == 200
    assert b'Aistent' in response.data


def test_download_word_preserves_romanian_and_paragraphs():
    response = create_app().test_client().post('/documents', data={
        'title': 'Cerere de concediu', 'content': 'Bună ziua!\nVă mulțumesc.'
    })
    assert response.status_code == 200
    assert 'attachment' in response.headers['Content-Disposition']
    document = Document(BytesIO(response.data))
    assert [p.text for p in document.paragraphs] == ['Cerere de concediu', 'Bună ziua!', 'Vă mulțumesc.']


def test_invalid_input():
    client = create_app().test_client()
    for data in ({}, {'title': 'Titlu', 'content': ' '}, {'title': 'x' * 201, 'content': 'Text'}, {'title': 'Titlu', 'content': '\x00'}):
        assert client.post('/documents', data=data).status_code == 400


def test_request_size_limit():
    response = create_app().test_client().post('/documents', data={'title': 'Titlu', 'content': 'x' * 300000})
    assert response.status_code == 413
