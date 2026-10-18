"""Fișiere private cu identificatori aleatori și verificare de proprietar."""
import mimetypes
import uuid
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from flask import abort, current_app, g
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from .db import db

ALLOWED = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi', '.mp3', '.wav', '.srt', '.txt', '.csv', '.docx', '.pdf', '.xlsx', '.pptx'}


def project(project_id):
    row = db().execute('SELECT * FROM projects WHERE id=? AND user_id=?', (project_id, g.user['id'])).fetchone()
    if not row:
        abort(404)
    return row


def file_record(file_id, project_id=None):
    row = db().execute('SELECT * FROM files WHERE id=? AND user_id=?', (file_id, g.user['id'])).fetchone()
    if not row or (project_id is not None and row['project_id'] != project_id):
        abort(404)
    return row


def path_for(row):
    return Path(current_app.config['STORAGE']) / row['id']


def store(project_id, name, data, mime=None):
    project(project_id)
    if len(data) > current_app.config['MAX_FILE_BYTES']:
        raise ValueError('Fișierul depășește limita de 50 MB.')
    used = db().execute('SELECT COALESCE(SUM(size),0) FROM files WHERE user_id=?', (g.user['id'],)).fetchone()[0]
    if used + len(data) > current_app.config['USER_STORAGE_BYTES']:
        raise ValueError('Spațiul disponibil pentru cont este epuizat.')
    identifier = uuid.uuid4().hex
    name = secure_filename(name) or 'fisier.bin'
    path = Path(current_app.config['STORAGE']) / identifier
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(0o600)
    try:
        db().execute('INSERT INTO files(id,project_id,user_id,name,mime,size) VALUES (?,?,?,?,?,?)', (identifier, project_id, g.user['id'], name, mime or mimetypes.guess_type(name)[0] or 'application/octet-stream', len(data)))
        db().commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return file_record(identifier)


def upload(project_id, item):
    suffix = Path(item.filename or '').suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError('Tip de fișier neacceptat.')
    data = item.stream.read(current_app.config['MAX_FILE_BYTES'] + 1)
    if not data:
        raise ValueError('Fișierul este gol.')
    if len(data) > current_app.config['MAX_FILE_BYTES']:
        raise ValueError('Fișierul depășește limita de 50 MB.')
    if suffix in {'.jpg', '.jpeg', '.png', '.webp'}:
        try:
            import io
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Format de imagine neacceptat.')
                if image.width * image.height > 24_000_000:
                    raise ValueError('Imaginea depășește limita de 24 megapixeli.')
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise ValueError('Imagine invalidă sau prea mare.') from error
    if suffix in {'.docx', '.xlsx', '.pptx'}:
        try:
            import io
            with ZipFile(io.BytesIO(data)) as archive:
                if sum(info.file_size for info in archive.infolist()) > 30 * 1024 * 1024 or len(archive.infolist()) > 3000:
                    raise ValueError('Document comprimat prea mare.')
        except BadZipFile as error:
            raise ValueError('Document Office invalid.') from error
    return store(project_id, item.filename, data)
