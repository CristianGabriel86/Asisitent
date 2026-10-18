"""Factory Aistent: backend modular cu date private și configurare din mediu."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, render_template


def create_app(test_config=None):
    app = Flask(__name__)
    root = Path(os.environ.get('AISTENT_DATA_DIR', str(Path(app.root_path).parent / 'instance'))).resolve()
    app.config.from_mapping(
        DATA_DIR=str(root), DATABASE=str(root / 'aistent.sqlite3'), STORAGE=str(root / 'files'),
        MAX_CONTENT_LENGTH=210 * 1024 * 1024, MAX_FORM_MEMORY_SIZE=1024 * 1024,
        MAX_FILE_BYTES=50 * 1024 * 1024, USER_STORAGE_BYTES=500 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('AISTENT_SECURE_COOKIES') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        AI_DAILY_USER_ESTIMATE_USD=float(os.environ.get('AISTENT_DAILY_USER_ESTIMATE_USD', '5')),
        AI_DAILY_GLOBAL_ESTIMATE_USD=float(os.environ.get('AISTENT_DAILY_GLOBAL_ESTIMATE_USD', '20')),
        ALLOW_REGISTRATION=os.environ.get('AISTENT_ALLOW_REGISTRATION', '1') == '1',
    )
    import math
    for cap in ('AI_DAILY_USER_ESTIMATE_USD', 'AI_DAILY_GLOBAL_ESTIMATE_USD'):
        if not math.isfinite(app.config[cap]) or app.config[cap] < 0:
            raise ValueError('Limitele de cost trebuie să fie valori finite, pozitive sau zero.')
    if test_config:
        app.config.update(test_config)
    for directory in (app.config['DATA_DIR'], app.config['STORAGE'], str(Path(app.config['DATABASE']).parent)):
        Path(directory).mkdir(parents=True, exist_ok=True, mode=0o700)
    key = app.config.get('SECRET_KEY') or os.environ.get('AISTENT_SESSION_KEY')
    if not key:
        keyfile = Path(app.config['DATA_DIR']) / 'session.key'
        try:
            with keyfile.open('x') as stream:
                keyfile.chmod(0o600)
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        key = keyfile.read_text().strip()
    if len(key) < 32:
        raise ValueError('AISTENT_SESSION_KEY trebuie să aibă minimum 32 de caractere.')
    app.config['SECRET_KEY'] = key
    from . import auth, db, workspace
    db.init_app(app)
    auth.install(app)
    app.register_blueprint(workspace.bp)

    @app.errorhandler(ValueError)
    def invalid(error):
        return render_template('error.html', message=str(error)), 400

    @app.errorhandler(413)
    def too_large(error):
        return render_template('error.html', message='Cererea depășește limita de 210 MB sau limita câmpurilor de text.'), 413

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(429)
    def http_error(error):
        return render_template('error.html', message=error.description), error.code

    return app
