"""Autentificare cu parole hash, sesiuni și protecție CSRF."""
import functools
import secrets
import time
from collections import defaultdict
from threading import Lock

from flask import Blueprint, abort, current_app, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from .db import db

bp = Blueprint('auth', __name__)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def install(app):
    app.extensions['login_attempts'] = defaultdict(list)
    app.extensions['login_lock'] = Lock()
    @app.before_request
    def security():
        g.user = db().execute('SELECT id,email FROM users WHERE id=?', (session.get('user_id'),)).fetchone()
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method == 'POST' and not current_app.config.get('CSRF_DISABLED_FOR_TESTS', False):
            token = request.form.get('csrf_token', '')
            if not secrets.compare_digest(token, session['csrf']):
                abort(400, 'Sesiune expirată sau token CSRF invalid. Reîncarcă pagina.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; media-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        return response
    app.register_blueprint(bp)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config['ALLOW_REGISTRATION']:
        abort(403, 'Înregistrarea conturilor este dezactivată.')
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if '@' not in email or len(email) > 254 or not 12 <= len(password) <= 256:
            error = 'Introdu un email valid și o parolă de 12–256 de caractere.'
        elif db().execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone():
            error = 'Contul nu poate fi creat cu această adresă.'
        else:
            from sqlite3 import IntegrityError
            try:
                db().execute('INSERT INTO users(email,password) VALUES (?,?)', (email, generate_password_hash(password)))
                db().commit()
            except IntegrityError:
                error = 'Contul nu poate fi creat cu această adresă.'
            else:
                return redirect(url_for('auth.login'))
    return render_template('auth.html', register=True, error=error), 400 if error else 200


@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        key = request.remote_addr
        now = time.monotonic()
        attempts = current_app.extensions['login_attempts']
        with current_app.extensions['login_lock']:
            for old_key in list(attempts):
                attempts[old_key] = [stamp for stamp in attempts[old_key] if now - stamp < 300]
                if not attempts[old_key]:
                    del attempts[old_key]
            attempts[key] = [stamp for stamp in attempts[key] if now - stamp < 300]
            if len(attempts[key]) >= 10:
                abort(429, 'Prea multe încercări. Reîncearcă peste 5 minute.')
            attempts[key].append(now)
        user = db().execute('SELECT * FROM users WHERE email=?', (request.form.get('email', '').strip().lower(),)).fetchone()
        password = request.form.get('password', '')
        if user and len(password) <= 256 and check_password_hash(user['password'], password):
            with current_app.extensions['login_lock']:
                attempts.pop(key, None)
            session.clear()
            session['user_id'] = user['id']
            session['csrf'] = secrets.token_urlsafe(32)
            return redirect(url_for('workspace.index'))
        error = 'Email sau parolă incorectă.'
    return render_template('auth.html', register=False, error=error), 400 if error else 200


@bp.post('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
