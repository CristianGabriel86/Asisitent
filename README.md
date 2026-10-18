# Aistent

Punct de pornire pentru un asistent de creare a documentelor Microsoft Word (.docx), cu interfață în română.

## Funcționalități

- Introducerea unui titlu și a conținutului.
- Export Word cu titlu și paragrafe, inclusiv diacritice.
- Generare în memorie, fără stocarea documentelor pe server.
- Validarea câmpurilor și limitarea dimensiunii cererilor.

Această versiune exportă textul introdus. Nu include încă redactare cu AI, conturi sau șabloane juridice. Nu necesită chei API.

## Pornire pentru dezvoltare

Necesită Python 3.12.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m flask --app aistent:create_app run --host 0.0.0.0 --port 5000
```

Serverul Flask inclus este destinat dezvoltării. Pentru producție sunt necesare un server WSGI, HTTPS și configurarea accesului.

## Teste

```bash
.venv/bin/python -m pytest -q
```

Testele verifică pagina principală, deschiderea fișierului Word generat, păstrarea diacriticelor și validarea cererilor.

## Structură

- `aistent/__init__.py`: aplicația Flask și generarea documentelor.
- `aistent/templates/index.html`: formularul web.
- `tests/`: teste funcționale.
- `requirements.txt`: dependențe aplicație.
- `requirements-dev.txt`: dependențe pentru dezvoltare și teste.

## Pași următori

Șabloane de documente, redactare asistată de AI și previzualizare înainte de export.
