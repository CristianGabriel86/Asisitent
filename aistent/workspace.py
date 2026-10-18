"""Proiecte, conversații, bibliotecă privată și operații confirmate explicit."""
import json
import re
import secrets
from io import BytesIO
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from werkzeug.exceptions import HTTPException

from . import ai, documents, media, storage, video_ai, research
from .auth import login_required
from .db import db
from .exports import EXPORTS

bp = Blueprint('workspace', __name__)


def back(project_id):
    return redirect(url_for('workspace.project_view', project_id=project_id))


def selected(project_id):
    identifiers = request.form.getlist('file_ids')
    if len(identifiers) > 8:
        raise ValueError('Selectează maximum 8 fișiere.')
    return [storage.file_record(identifier, project_id) for identifier in dict.fromkeys(identifiers)]


def valid_text():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        raise ValueError('Completează titlul și conținutul.')
    if len(title) > 200 or len(content) > 100_000:
        raise ValueError('Maximum 200 de caractere pentru titlu și 100.000 pentru conținut.')
    if any((ord(char) < 32 and char not in '\n\r\t') or 0xD800 <= ord(char) <= 0xDFFF or ord(char) in {0xFFFE, 0xFFFF} for char in title + content):
        raise ValueError('Textul conține caractere de control nepermise.')
    return title, content


@bp.get('/')
@login_required
def index():
    projects = db().execute('SELECT * FROM projects WHERE user_id=? ORDER BY id DESC', (g.user['id'],)).fetchall()
    return render_template('index.html', projects=projects)


@bp.post('/projects')
@login_required
def create_project():
    title = request.form.get('title', '').strip()
    if not 1 <= len(title) <= 200:
        abort(400, 'Titlul proiectului trebuie să aibă 1–200 de caractere.')
    cursor = db().execute('INSERT INTO projects(user_id,title) VALUES (?,?)', (g.user['id'], title))
    db().commit()
    return back(cursor.lastrowid)


@bp.get('/projects/<int:project_id>')
@login_required
def project_view(project_id):
    project = storage.project(project_id)
    files = db().execute('SELECT * FROM files WHERE project_id=? AND user_id=? ORDER BY created,id', (project_id, g.user['id'])).fetchall()
    messages = [dict(row) for row in db().execute('SELECT * FROM messages WHERE project_id=? ORDER BY id', (project_id,))]
    for message in messages:
        message['sources'] = json.loads(message['sources'])
    jobs = db().execute('SELECT * FROM quotes WHERE project_id=? AND user_id=? ORDER BY created DESC,id DESC LIMIT 30', (project_id, g.user['id'])).fetchall()
    return render_template('project.html', project=project, files=files, messages=messages, jobs=jobs, actions=ai.ACTIONS, available={action: ai.configured(action) for action in ai.ACTIONS})


@bp.post('/projects/<int:project_id>/upload')
@login_required
def upload(project_id):
    storage.project(project_id)
    items = request.files.getlist('files')
    if not 1 <= len(items) <= 8:
        raise ValueError('Încarcă între 1 și 8 fișiere odată.')
    for item in items:
        storage.upload(project_id, item)
    flash('Fișierele au fost adăugate în proiect.')
    return back(project_id)


@bp.get('/files/<file_id>')
@login_required
def download(file_id):
    record = storage.file_record(file_id)
    preview = request.args.get('preview') == '1'
    safe_mimes = {'image/png', 'image/jpeg', 'image/webp', 'video/mp4', 'audio/mpeg', 'audio/wav'}
    return send_file(storage.path_for(record), mimetype=record['mime'], as_attachment=not (preview and record['mime'] in safe_mimes), download_name=record['name'], conditional=True)


@bp.post('/files/<file_id>/delete')
@login_required
def delete(file_id):
    record = storage.file_record(file_id)
    storage.path_for(record).unlink(missing_ok=True)
    db().execute('DELETE FROM files WHERE id=? AND user_id=?', (file_id, g.user['id']))
    db().commit()
    return back(record['project_id'])


@bp.get('/files/<file_id>/edit')
@login_required
def edit_document(file_id):
    record = storage.file_record(file_id)
    try:
        content = documents.extract(storage.path_for(record), record['name'])
    except ValueError:
        raise
    except Exception as error:
        raise ValueError('Documentul nu poate fi citit sau este protejat prin parolă.') from error
    return render_template('editor.html', project=storage.project(record['project_id']), title=Path(record['name']).stem, content=content)


@bp.post('/projects/<int:project_id>/documents')
@login_required
def document_export(project_id):
    storage.project(project_id)
    title, content = valid_text()
    kind = request.form.get('format', 'docx')
    if kind == 'estimate':
        data = documents.estimate(content, request.form.get('vat', '21'))
        name, mime = 'deviz-electric.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        if kind not in EXPORTS:
            raise ValueError('Format necunoscut.')
        exporter, name, mime = EXPORTS[kind]
        data = exporter(title, content)
    storage.store(project_id, name, data, mime)
    flash('Fișierul a fost generat și salvat în bibliotecă.')
    return back(project_id)


@bp.post('/documents')
@login_required
def legacy_document_export():
    """Export direct pentru compatibilitate; necesită autentificare."""
    title, content = valid_text()
    kind = request.form.get('format', 'docx')
    if kind not in EXPORTS:
        raise ValueError('Format necunoscut.')
    exporter, name, mime = EXPORTS[kind]
    return send_file(BytesIO(exporter(title, content)), as_attachment=True, download_name=name, mimetype=mime)


@bp.post('/projects/<int:project_id>/bibliography')
@login_required
def bibliography(project_id):
    storage.project(project_id)
    query = request.form.get('query', '')
    text = research.bibliography(query)
    storage.store(project_id, 'bibliografie-crossref.txt', text.encode('utf-8'), 'text/plain')
    db().execute('INSERT INTO messages(project_id,role,content) VALUES (?,?,?)', (project_id, 'assistant', text))
    db().commit()
    flash('Referințele Crossref au fost salvate. Verifică relevanța lor înainte de citare.')
    return back(project_id)


@bp.post('/projects/<int:project_id>/photo')
@login_required
def photo(project_id):
    storage.project(project_id)
    records = selected(project_id)
    if len(records) != 1 or Path(records[0]['name']).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
        raise ValueError('Selectează o singură fotografie.')
    data = media.edit_photo(storage.path_for(records[0]), request.form.get('brightness', '1'), request.form.get('saturation', '1'), request.form.get('background') or None)
    storage.store(project_id, 'fotografie-editata.png', data, 'image/png')
    return back(project_id)


@bp.post('/projects/<int:project_id>/video')
@login_required
def video(project_id):
    storage.project(project_id)
    records = selected(project_id)
    paths = [storage.path_for(record) for record in records]
    music_id = request.form.get('music_id')
    subtitle_id = request.form.get('subtitle_id')
    music = storage.file_record(music_id, project_id) if music_id else None
    subtitles = storage.file_record(subtitle_id, project_id) if subtitle_id else None
    if music and Path(music['name']).suffix.lower() not in {'.mp3', '.wav'}:
        raise ValueError('Selectează un fișier MP3 sau WAV pentru sunet.')
    if subtitles and Path(subtitles['name']).suffix.lower() != '.srt':
        raise ValueError('Subtitrările trebuie să fie în format SRT UTF-8.')
    data = media.video(paths, operation=request.form.get('operation', 'trim'), resolution=request.form.get('resolution', '720p'), start=request.form.get('start', '0'), end=request.form.get('end', ''), speed=request.form.get('speed', '1'), brightness=request.form.get('brightness', '0'), saturation=request.form.get('saturation', '1'), music=storage.path_for(music) if music else None, subtitles=storage.path_for(subtitles) if subtitles else None)
    storage.store(project_id, 'montaj.mp4', data, 'video/mp4')
    return back(project_id)


@bp.post('/projects/<int:project_id>/quote')
@login_required
def quote(project_id):
    storage.project(project_id)
    action = request.form.get('action', 'chat')
    if action not in ai.ACTIONS:
        raise ValueError('Operație AI necunoscută.')
    prompt = request.form.get('prompt', '').strip()
    if not 1 <= len(prompt) <= 12_000:
        raise ValueError('Instrucțiunile trebuie să aibă 1–12.000 de caractere.')
    records = selected(project_id)
    if action == 'image_edit' and (len(records) != 1 or Path(records[0]['name']).suffix.lower() not in {'.jpg', '.jpeg', '.webp', '.png'}):
        raise ValueError('Editarea AI necesită o singură fotografie.')
    if action == 'image_generate' and records:
        raise ValueError('Pentru a folosi o imagine existentă, alege editarea AI.')
    if action == 'video_generate' and (len(records) > 1 or (records and Path(records[0]['name']).suffix.lower() not in {'.jpg', '.jpeg', '.webp', '.png'})):
        raise ValueError('Generarea video acceptă text și, opțional, o singură fotografie.')
    payload = {'prompt': prompt, 'file_ids': [record['id'] for record in records], 'model': ai.model(action)}
    if action == 'video_edit' and (len(records) != 1 or Path(records[0]['name']).suffix.lower() not in {'.mp4', '.mov', '.avi'}):
        raise ValueError('Editarea video AI necesită un singur videoclip MP4, MOV sau AVI.')
    if action.startswith('video_'):
        payload['video_config'] = video_ai.config(action)
        if records and action == 'video_generate' and '$IMAGE' not in payload['video_config']['input'].values():
            raise ValueError('Modelul configurat nu acceptă fotografie de referință; configurează câmpul $IMAGE sau generează doar din text.')
    amount = ai.cost(action)
    identifier = secrets.token_urlsafe(24)
    db().execute('INSERT INTO quotes(id,user_id,project_id,action,payload,estimate) VALUES (?,?,?,?,?,?)', (identifier, g.user['id'], project_id, action, json.dumps(payload), amount))
    db().commit()
    return redirect(url_for('workspace.quote_view', quote_id=identifier))


@bp.get('/quotes/<quote_id>')
@login_required
def quote_view(quote_id):
    row = db().execute('SELECT * FROM quotes WHERE id=? AND user_id=?', (quote_id, g.user['id'])).fetchone()
    if not row:
        abort(404)
    return render_template('quote.html', quote=row, payload=json.loads(row['payload']), action=ai.ACTIONS[row['action']])


@bp.post('/quotes/<quote_id>/confirm')
@login_required
def confirm(quote_id):
    row = db().execute('SELECT * FROM quotes WHERE id=? AND user_id=?', (quote_id, g.user['id'])).fetchone()
    if not row:
        abort(404)
    if request.form.get('consent') != 'yes':
        raise ValueError('Confirmă costul și transmiterea fișierelor selectate către furnizor.')
    payload = json.loads(row['payload'])
    if (payload['model'] != ai.model(row['action']) or row['estimate'] != ai.cost(row['action']) or (row['action'].startswith('video_') and payload.get('video_config') != video_ai.config(row['action']))):
        raise ValueError('Configurația sau estimarea s-a schimbat. Creează o estimare nouă.')
    # Serialize consent and the estimated-spend check, including concurrent requests.
    db().execute('BEGIN IMMEDIATE')
    spent = db().execute("SELECT COALESCE(SUM(estimate),0) FROM quotes WHERE user_id=? AND status != 'pending' AND created >= datetime('now','-1 day')", (g.user['id'],)).fetchone()[0]
    global_spent = db().execute("SELECT COALESCE(SUM(estimate),0) FROM quotes WHERE status != 'pending' AND created >= datetime('now','-1 day')").fetchone()[0]
    if spent + row['estimate'] > current_app.config['AI_DAILY_USER_ESTIMATE_USD'] or global_spent + row['estimate'] > current_app.config['AI_DAILY_GLOBAL_ESTIMATE_USD']:
        db().rollback()
        raise ValueError('Limita zilnică de cost estimat a fost atinsă. Aceasta nu înlocuiește limita de facturare de la furnizor.')
    updated = db().execute("UPDATE quotes SET status='running' WHERE id=? AND user_id=? AND status='pending' AND created >= datetime('now', '-15 minutes')", (quote_id, g.user['id']))
    db().commit()
    if updated.rowcount != 1:
        raise ValueError('Cererea a fost deja confirmată sau estimarea a expirat. Nu este repetată.')
    try:
        records = [storage.file_record(identifier, row['project_id']) for identifier in payload['file_ids']]
        action = row['action']
        if action in {'chat', 'search'}:
            history = db().execute('SELECT role,content FROM messages WHERE project_id=? ORDER BY id DESC LIMIT 12', (row['project_id'],)).fetchall()[::-1]
            result = ai.text_result(action, payload, records, history)
            user_text = payload['prompt'] + ('\n\nFișiere: ' + ', '.join(record['name'] for record in records) if records else '')
            db().execute('INSERT INTO messages(project_id,role,content) VALUES (?,?,?)', (row['project_id'], 'user', user_text))
            db().execute('INSERT INTO messages(project_id,role,content,sources) VALUES (?,?,?,?)', (row['project_id'], 'assistant', result['text'], json.dumps(result['sources'])))
            storage.store(row['project_id'], 'raspuns-asistent.txt', result['text'].encode('utf-8'), 'text/plain')
        elif action in {'image_generate', 'image_edit'}:
            result = ai.image_result(action, payload, records)
            storage.store(row['project_id'], result['name'], result['data'], result['mime'])
        else:
            result = video_ai.create(action, payload, records)
            remote_id = result.get('id', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,150}', remote_id):
                raise ValueError('Furnizorul nu a returnat un identificator video valid.')
            db().execute("UPDATE quotes SET status='queued',remote_id=? WHERE id=?", (remote_id, quote_id))
            db().commit()
            flash('Generarea video a fost trimisă. Verifică starea din lista de operații AI.')
            return back(row['project_id'])
        db().execute("UPDATE quotes SET status='completed' WHERE id=?", (quote_id,))
        db().commit()
    except Exception as error:
        db().execute("UPDATE quotes SET status='failed' WHERE id=?", (quote_id,))
        db().commit()
        if isinstance(error, (ValueError, HTTPException)):
            raise
        raise ValueError('Operația AI nu a fost finalizată local. Verifică utilizarea la furnizor înainte să creezi o cerere nouă.') from error
    flash('Operația AI a fost finalizată. Rezultatul este în proiect.')
    return back(row['project_id'])


@bp.post('/quotes/<quote_id>/poll')
@login_required
def poll(quote_id):
    row = db().execute('SELECT * FROM quotes WHERE id=? AND user_id=?', (quote_id, g.user['id'])).fetchone()
    if not row:
        abort(404)
    if row['status'] != 'queued' or not row['remote_id']:
        raise ValueError('Acest job video nu este în așteptare.')
    result = video_ai.status(row['remote_id'])
    if result.get('status') == 'succeeded':
        updated = db().execute("UPDATE quotes SET status='downloading' WHERE id=? AND status='queued'", (quote_id,))
        db().commit()
        if updated.rowcount != 1:
            raise ValueError('Rezultatul este deja descărcat de o altă cerere.')
        try:
            data = video_ai.download(result)
            storage.store(row['project_id'], 'video-ai.mp4', data, 'video/mp4')
        except Exception:
            db().execute("UPDATE quotes SET status='queued' WHERE id=?", (quote_id,))
            db().commit()
            raise
        db().execute("UPDATE quotes SET status='completed' WHERE id=?", (quote_id,))
        flash('Videoclipul este disponibil în biblioteca proiectului.')
    elif result.get('status') in {'failed', 'canceled'}:
        db().execute("UPDATE quotes SET status='failed' WHERE id=?", (quote_id,))
        flash('Furnizorul a raportat eșecul generării. Verifică detaliile în contul furnizorului.')
    else:
        flash('Videoclipul este încă în procesare; nu a fost trimisă o generare nouă.')
    db().commit()
    return back(row['project_id'])
