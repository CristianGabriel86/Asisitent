"""Adaptor Replicate bazat pe versiune și schema reală a modelului ales."""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from .storage import path_for
from .media import probe


def config(action):
    prefix = 'AISTENT_VIDEO_EDIT' if action == 'video_edit' else 'AISTENT_VIDEO_GENERATE'
    version = os.environ.get(prefix + '_VERSION', '')
    try:
        template = json.loads(os.environ.get(prefix + '_INPUT', '{}'))
    except json.JSONDecodeError as error:
        raise ValueError('Schema de intrare a modelului video nu este JSON valid.') from error
    if not re.fullmatch('[0-9a-f]{64}', version) or not isinstance(template, dict) or '$PROMPT' not in template.values():
        raise ValueError('Configurează versiunea Replicate (64 caractere hex) și schema JSON cu valoarea $PROMPT pentru modelul video ales.')
    if any(not isinstance(value, (str, int, float, bool, list, dict, type(None))) for value in template.values()):
        raise ValueError('Schema video conține valori neacceptate.')
    if action == 'video_edit' and '$VIDEO' not in template.values():
        raise ValueError('Schema modelului de editare video trebuie să conțină valoarea $VIDEO.')
    return {'version': version, 'input': template}


def available(action):
    if not os.environ.get('AISTENT_VIDEO_KEY'):
        return False
    try:
        config(action)
        return True
    except ValueError:
        return False


def api(method, path, **kwargs):
    key = os.environ.get('AISTENT_VIDEO_KEY')
    if not key:
        raise ValueError('Cheia Replicate nu este configurată.')
    try:
        response = requests.request(method, 'https://api.replicate.com/v1/' + path, headers={'Authorization': 'Bearer ' + key}, timeout=(10, 90), allow_redirects=False, **kwargs)
    except requests.RequestException as error:
        raise ValueError('Replicate nu a răspuns. Verifică utilizarea la furnizor; cererea nu este repetată automat.') from error
    if not response.ok or response.is_redirect:
        raise ValueError(f'Replicate a respins cererea (HTTP {response.status_code}). Verifică versiunea modelului, schema și accesul contului.')
    return response.json()


def create(action, payload, records):
    inputs = dict(payload['video_config']['input'])
    asset_url = None
    if records:
        record = records[0]
        if action == 'video_edit':
            probe(path_for(record))
        with path_for(record).open('rb') as stream:
            asset = api('POST', 'files', files={'content': (record['name'], stream, record['mime'])})
        asset_url = asset.get('urls', {}).get('get')
        if not isinstance(asset_url, str) or urlparse(asset_url).scheme != 'https':
            raise ValueError('Furnizorul nu a returnat o referință validă pentru fișier.')
    for key, value in list(inputs.items()):
        if value == '$PROMPT':
            inputs[key] = payload['prompt']
        elif value in ('$IMAGE', '$VIDEO'):
            if asset_url:
                inputs[key] = asset_url
            else:
                del inputs[key]
    return api('POST', 'predictions', json={'version': payload['video_config']['version'], 'input': inputs})


def status(identifier):
    if not re.fullmatch('[A-Za-z0-9_-]{1,150}', identifier):
        raise ValueError('Identificator video invalid.')
    return api('GET', 'predictions/' + identifier)


def download(result):
    output = result.get('output')
    if isinstance(output, list) and len(output) == 1:
        output = output[0]
    if not isinstance(output, str):
        raise ValueError('Modelul nu a returnat un URL video unic. Verifică schema de ieșire a modelului ales.')
    parsed = urlparse(output)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in {None, 443} or not (host == 'replicate.delivery' or host.endswith('.replicate.delivery')):
        raise ValueError('Rezultatul video nu este pe un domeniu Replicate Delivery acceptat.')
    # Never forward the API key to a file URL or follow arbitrary redirects.
    try:
        with requests.get(output, timeout=(10, 90), stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError('Descărcarea rezultatului video nu a reușit.')
            data = bytearray()
            for chunk in response.iter_content(64 * 1024):
                data.extend(chunk)
                if len(data) > 50 * 1024 * 1024:
                    raise ValueError('Videoclipul depășește limita de 50 MB.')
            return bytes(data)
    except requests.RequestException as error:
        raise ValueError('Nu s-a putut descărca rezultatul. Poți verifica din nou starea fără a genera alt videoclip.') from error
