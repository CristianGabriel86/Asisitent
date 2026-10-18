"""Persistență SQLite, izolată de fișierele publice."""
import sqlite3
from flask import current_app, g

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, project_id INTEGER NOT NULL, user_id INTEGER NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, sources TEXT DEFAULT '[]', created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, project_id INTEGER NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL, estimate REAL NOT NULL, status TEXT DEFAULT 'pending', remote_id TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
'''


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], timeout=20)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


def init_app(app):
    @app.teardown_appcontext
    def close(error):
        connection = g.pop('db', None)
        if connection is not None:
            connection.close()
    with app.app_context():
        db().executescript(SCHEMA)
        db().commit()
