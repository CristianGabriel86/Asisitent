# Aistent

Aplicație web Python, cu interfață în română, pentru generarea fișierelor din conținutul introdus de utilizator.

## Funcționalități

| Export | Conținut de introdus | Rezultat |
| --- | --- | --- |
| Word | Titlu și text | `.docx`, cu paragrafe și diacritice |
| PDF | Titlu și text | `.pdf`, cu font Unicode inclus |
| Excel | Date CSV cu antet, separate prin virgulă | `.xlsx`, antet evidențiat și filtre |
| Grafic | CSV cu două coloane: etichetă și valoare numerică | Grafic cu bare `.png` |
| Lucrare academică | Text și secțiuni marcate `## Nume secțiune` | `.docx` cu titluri de secțiune |

Fără marcaje `## `, exportul academic folosește textul ca introducere și adaugă secțiuni de completat: rezumat, revizuirea literaturii, metodologie, rezultate, discuții, concluzii și bibliografie. Autorul trebuie să verifice structura cerută de instituție și să furnizeze sursele reale. Aplicația nu generează text cu AI, nu caută surse și nu garantează respectarea unui stil de citare.

Fișierele sunt generate în memorie, fără salvarea documentelor pe server. Nu sunt necesare chei API. Celulele Excel sunt exportate ca text literal, inclusiv valorile care încep cu `=`.

## Instalare și pornire

Necesită Python 3.12. Din directorul proiectului:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python run.py
```

În Windows PowerShell, activează mediul cu `.venv\Scripts\Activate.ps1` în locul comenzii `source`.

Deschide adresa afișată în terminal în cazul rulării pe calculatorul tău. Pentru mediul cloud, pornește cu `python run.py --host 0.0.0.0 --port 5000` și folosește mecanismul de acces oferit de platformă. Serverul inclus este pentru dezvoltare; publicarea unei aplicații necesită un server WSGI, HTTPS și configurarea accesului.

Pentru instalarea exclusivă a aplicației: `python -m pip install -r requirements.txt`. Numele standard al fișierului este `requirements.txt`.

## Utilizare

1. Alege tipul exportului.
2. Completează titlul și conținutul.
3. Apasă „Generează și descarcă”.

Exemplu CSV pentru Excel sau grafice:

```csv
Lună,Venit
Ianuarie,1200
Februarie,1500
```

Folosește punctul pentru zecimale și ghilimele CSV pentru câmpuri care conțin virgule. Excel acceptă maximum 1.000 de rânduri, inclusiv antetul, și 50 de coloane. Graficele acceptă maximum 100 de valori finite și exact două coloane. Conținutul este limitat la 100.000 de caractere.

Exemplu pentru o lucrare academică:

```text
## Rezumat
Rezumatul redactat de autor.
## Introducere
Contextul și obiectivele lucrării.
## Metodologie
Metoda utilizată.
## Bibliografie
Referințele reale utilizate.
```

## Verificare

```bash
python -m pytest -q
python -m pip check
```

Testele deschid fișierele Word, PDF, Excel și PNG generate, verifică diacriticele, structura academică și tratarea datelor invalide.

## Structură

```text
aistent/
  __init__.py           # Rute web și validare
  exports.py            # Generatoare Word, PDF, Excel și grafice
  templates/index.html  # Formular în română
tests/test_app.py       # Teste funcționale
run.py                  # Script Python de pornire
requirements.txt        # Dependențe aplicație
requirements-dev.txt    # Dependențe dezvoltare și teste
```

## Salvarea modificărilor în GitHub

Din checkout-ul conectat, verifică mai întâi fișierele și ramura:

```bash
git status
git diff
```

Pentru a salva această versiune direct în `main`:

```bash
git add README.md requirements.txt requirements-dev.txt run.py aistent tests
git commit -m "Add PDF, Excel, charts and academic document exports"
git push origin HEAD:main
```

Dacă modificările au fost deja salvate într-un commit, execută doar comanda `git push`. Nu adăuga mediul `.venv`, chei API sau fișiere `.env`. Dacă `main` are între timp alte modificări, integrează-le înainte de push; nu folosi `--force`.

Pentru revizuire prin pull request, publică în schimb într-o ramură nouă cu `git push origin HEAD:feature/document-exports`, apoi deschide un pull request spre `main` în GitHub.

## Extensii viitoare

Redactare cu AI printr-un furnizor configurabil, șabloane academice, citări validate și exportul lucrărilor academice direct în PDF.
