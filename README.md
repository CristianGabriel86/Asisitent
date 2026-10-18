# Aistent

Asistent web modular în limba română pentru documente, proiecte academice, devize electrice, fotografii și videoclipuri. Backend Python/Flask, interfață adaptată pentru telefon și calculator, SQLite și fișiere private pe server.

## Ce funcționează

| Modul | Funcții locale / fără cheie API |
| --- | --- |
| Conturi | Înregistrare, autentificare, parole hash scrypt, deconectare, CSRF și verificarea proprietarului fiecărui proiect/fișier |
| Proiecte | Bibliotecă privată, încărcare multiplă, istoric conversații, descărcare și ștergere fișiere |
| Documente | Word, PDF cu diacritice, Excel din CSV, PowerPoint și grafice PNG |
| Editare documente | Extragere text/date din DOCX, PDF, XLSX, PPTX, TXT și CSV, editare în formular și export nou |
| Academic | Secțiuni `## Titlu`, structură inițială cu rezumat, introducere, literatură, metodologie, rezultate, discuții, concluzii și bibliografie |
| Calcule | Analiză numerică (sumă, medie, minim, maxim, număr observații); deviz electric în RON cu materiale, manoperă și TVA configurabil |
| Fotografii | Încărcare JPG/PNG/WebP, luminozitate, saturație, fundal pentru zonele deja transparente |
| Video | Încărcare MP4/MOV/AVI; tăiere, unire, montaj din fotografii și clipuri, viteză 0,5–2×, culori, iluminare, sunet MP3/WAV și subtitrări SRT |
| Rezultate media | MP4 H.264/AAC la 480p, 720p sau 1080p; previzualizare privată în browser înainte de descărcare |

### Integrări externe implementate, de activat și validat cu un cont real

| Furnizor | Funcții | Cerințe |
| --- | --- | --- |
| OpenAI Responses | Conversații în română, analiză documente/fotografii, explicații tehnice, căutare web cu linkuri sursă | Cheie, model cu acces și estimare de cost pozitivă |
| OpenAI Images | Generare imagini, inclusiv prompturi fotorealiste; editări de fundal, obiecte, culori și amenajări | Cheie cu acces la modelul de imagini și confirmarea costului |
| Replicate | Generare video din text sau fotografie și editarea unui video încărcat | Cheie, versiunea reală a modelului și schema exactă a intrării/ieșirii |
| Crossref | Căutare bibliografică și salvarea a maximum 5 referințe reale cu DOI | Acces HTTPS; fără cheie API |

Recunoașterea pieselor, echipamentelor și defectelor este realizată prin modelul vizual, când este activat. Recomandările sunt orientative, nu o certificare a siguranței instalației. Analiza video folosește **maximum 6 cadre eșantionate**, nu urmărire continuă a mișcării, analiză audio sau detectarea tuturor defectelor.

Modificările semantice din video (eliminarea/adăugarea obiectelor, înlocuirea fundalului, schimbarea stilului) depind de capabilitățile modelului Replicate ales; nu sunt garantate de un adaptor generic. Generarea AI poate dura și poate fi refuzată de furnizor. Disponibilitatea și tarifele trebuie verificate în contul furnizorului.

## Instalare

Necesită **Python 3.12**, **FFmpeg** și **FFprobe** cu codec H.264 și filtrul `subtitles` (libass).

Pe Debian/Ubuntu, dacă FFmpeg lipsește:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

Din directorul repository-ului:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python run.py
```

În Windows PowerShell, activează mediul cu `.venv\Scripts\Activate.ps1`. Instalează separat FFmpeg și adaugă-l în `PATH`.

Pentru mediul cloud:

```bash
.venv/bin/python run.py --host 0.0.0.0 --port 5000
```

Numele standard al fișierului de dependențe este `requirements.txt`. Pentru instalarea exclusivă a aplicației: `python -m pip install -r requirements.txt`.

### Primii pași

1. Creează un cont cu o parolă de cel puțin 12 caractere și autentifică-te.
2. Creează un proiect.
3. Încarcă documentele, fotografiile sau videoclipurile în acel proiect.
4. Generează documente sau folosește instrumentele foto/video locale.
5. Rezultatele apar în biblioteca proiectului. MP4 și fotografiile pot fi previzualizate; documentele pot fi descărcate sau importate în editor.
6. Pentru AI, selectează operația și fișierele, citește estimarea și confirmă explicit transmiterea datelor și costul.

## Configurarea AI și a costurilor

Cheile se injectează în proces dintr-un secret manager sau din setările securizate ale mediului. **Nu le introduce în Git, formulare web, capturi de ecran sau mesaje.** Aplicația citește variabilele de mediu; `.env.example` documentează numele, dar nu este încărcat automat.

- `AISTENT_AI_KEY`: cheia OpenAI, folosită numai pentru `api.openai.com`.
- `AISTENT_VIDEO_KEY`: cheia Replicate, folosită numai pentru `api.replicate.com`.
- `AISTENT_TEXT_MODEL`: implicit `gpt-4.1-mini`.
- `AISTENT_IMAGE_MODEL`: implicit `gpt-image-1`.
- `AISTENT_COST_CHAT_USD`, `AISTENT_COST_SEARCH_USD`, `AISTENT_COST_IMAGE_GENERATE_USD`, `AISTENT_COST_IMAGE_EDIT_USD`, `AISTENT_COST_VIDEO_GENERATE_USD`, `AISTENT_COST_VIDEO_EDIT_USD`: estimări USD/cerere stabilite de administrator după verificarea tarifelor și a utilizării tipice. Valoarea absentă sau `0` dezactivează operația.
- `AISTENT_DAILY_USER_ESTIMATE_USD`: plafon estimat pe cont în ultimele 24 de ore, implicit 5 USD.
- `AISTENT_DAILY_GLOBAL_ESTIMATE_USD`: plafon estimat pentru întreaga aplicație în ultimele 24 de ore, implicit 20 USD.

**Estimările configurate nu sunt cotații ale furnizorilor și nu se calculează din factura reală.** Setează limite financiare și în conturile API. Cererile cu rezultat incert sau eșuat consumă plafonul estimat, fiindcă facturarea poate fi deja efectuată. Sesiunea de confirmare expiră după 15 minute și este consumată atomic, o singură dată. Schimbarea modelului, a costului sau a schemei video impune o estimare nouă. Generările nu au retries automate.

Conversațiile trimit cel mult ultimele 12 mesaje, fișierele selectate și maximum 2.500 tokenuri de răspuns solicitate. Căutarea web permite cel mult un apel de instrument. Imaginile se generează la 1024×1024, calitate redusă. Actualizează estimările când schimbi parametrii sau modelul.

Cheile sunt configurate la nivelul procesului serverului, nu separat pentru fiecare cont creat în aplicație. Conturile autorizate folosesc resursele acelui server. Nu deschide înregistrarea publică pe un server cu chei plătite fără control suplimentar al accesului și al facturării.

### Alegerea modelului video Replicate

Nu este inclus un identificator fictiv și nici un model video activat implicit. Pentru fiecare operație alege un model care suportă intrarea dorită și verifică în pagina sa API versiunea, schema și tarifele:

- `AISTENT_VIDEO_GENERATE_VERSION`: versiune reală, 64 de caractere hexazecimale.
- `AISTENT_VIDEO_GENERATE_INPUT`: obiect JSON cu parametrii reali ai modelului; valoarea `$PROMPT` se înlocuiește cu mesajul, iar `$IMAGE` cu fotografia selectată. Câmpul `$IMAGE` este omis când nu selectezi o fotografie.
- `AISTENT_VIDEO_EDIT_VERSION` și `AISTENT_VIDEO_EDIT_INPUT`: versiunea și schema modelului de editare; sunt necesare valorile `$PROMPT` și `$VIDEO`.

Exemple **ilustrative de schemă, nu configurații garantate pentru orice model**:

```json
{"prompt":"$PROMPT","image":"$IMAGE","duration":4}
```

```json
{"prompt":"$PROMPT","video":"$VIDEO"}
```

Numele câmpurilor și parametrii suplimentari trebuie copiați din schema modelului ales. Substituția se face în valorile de la primul nivel. Modelul trebuie să returneze un URL video unic sau o listă cu un singur URL, pe `replicate.delivery` ori un subdomeniu al acestuia. Alte scheme de ieșire necesită un adaptor specific. Parametrii (durată/rezoluție) sunt afișați înainte de confirmare.

Fișierul de intrare este încărcat la Replicate după confirmare, apoi se creează un job. Butonul „Verifică starea” citește starea fără a crea o nouă generare. La final, fișierul este copiat în biblioteca privată. Fișierele încărcate la furnizor respectă politica sa de retenție; ștergerea locală nu le șterge automat de la furnizor.

Integrarea video nu folosește Sora: [SDK-ul oficial OpenAI](https://github.com/openai/openai-python/blob/main/src/openai/resources/videos.py) marchează API-ul Sora cu data de închidere 24 septembrie 2026.

### Rețea

Permite conexiuni HTTPS către:

- `api.openai.com`
- `api.replicate.com`
- `replicate.delivery` și `*.replicate.delivery`
- `api.crossref.org`

Cheile nu sunt trimise către domeniile de descărcare. Redirecționările către destinații arbitrare sunt refuzate. Verificarea TLS rămâne activă.

## Exemple de documente și calcule

Excel, grafic sau analiză numerică:

```csv
Lună,Venit
Ianuarie,1200
Februarie,1500
```

Deviz electric (cantități și prețuri unitare în RON):

```csv
Descriere,UM,Cantitate,Material,Manopera
Cablu electric,m,100,4.5,3
Priză,buc,10,25,30
```

Totalul fiecărei linii = cantitate × material unitar + cantitate × manoperă unitară. Componentele se rotunjesc la bani folosind `Decimal`, apoi se calculează TVA. Cota implicită din formular este **21%**, editabilă; verifică regimul aplicabil lucrării. Nu sunt incluse tarife de piață, norme de proiectare, dimensionarea circuitelor sau avizarea instalației.

Pentru lucrări academice și prezentări, secțiunile încep cu `## `:

```text
## Introducere
Contextul și obiectivele.
## Metodologie
Metoda utilizată.
## Bibliografie
Referințele reale utilizate.
```

Crossref returnează metadate și DOI reale din registru, nu verifică automat conținutul articolului, relevanța sau conformitatea cu APA/IEEE. Citările și argumentele trebuie verificate de autor. În lipsa accesului la registru, aplicația raportează eroarea, fără referințe inventate.

## Date, securitate și limite

- `instance/` conține baza SQLite, fișierele private și cheia de sesiune. Poți seta `AISTENT_DATA_DIR` la un volum persistent. Directorul este ignorat de Git.
- Fă copii de siguranță protejate ale datelor și ale cheii de sesiune. Cheia este generată local cu permisiuni restrictive sau furnizată prin `AISTENT_SESSION_KEY` (minimum 32 de caractere).
- Parolele sunt hash-uite cu scrypt; formularele POST folosesc CSRF. ID-urile de fișiere sunt aleatorii, dar accesul este verificat și în baza de date, pentru fiecare operație.
- Maximum 8 fișiere/încărcare sau operație; 50 MB/fișier, 500 MB/cont, 210 MB/cerere, imagini de maximum 24 megapixeli. Limita de spațiu este verificată la salvare; nu există rezervare atomică de spațiu pentru încărcări simultane.
- Videoclipuri de maximum 5 minute/sursă și 4K la intrare; montaj de maximum 5 minute de clipuri, plus maximum 3 secunde/fotografie. Procesarea este sincronă, cu timeout de 120 secunde; clipurile mari pot necesita împărțire.
- Unirea mai multor surse produce video **fără sunet**. Muzica se poate adăuga într-o operație ulterioară. Sunetul nou se mixează cu cel original, fără editor de piste, fade sau reglaj separat de volum. Subtitrările sunt arse în imagine dintr-un fișier SRT UTF-8.
- Importul documentelor reconstruiește textul/datele, nu păstrează fidel layout-ul, imaginile, formulele, comentariile sau stilurile originale. PDF-urile scanate necesită OCR, neinclus. Formulele Excel sunt exportate ca text literal în exportul de tabel.
- Excel/analiză: maximum 1.000 rânduri și 50 coloane; grafice: două coloane, maximum 100 valori. Conținut: maximum 100.000 caractere. Prezentări: maximum 40 secțiuni.
- Nu sunt incluse recuperarea parolei, verificarea emailului, MFA, criptarea la repaus, OCR, transcrierea audio, tracking video, cronologie de montaj avansată sau un procesor de joburi distribuit.

### Publicare în producție

`run.py` pornește un server de **dezvoltare**, nu o aplicație găzduită public. Înainte de publicare, folosește un server WSGI, HTTPS și volum persistent; setează `AISTENT_SECURE_COOKIES=1` sub HTTPS și `AISTENT_ALLOW_REGISTRATION=0` după crearea conturilor permise. Configurează limitele de upload și timeout și în reverse proxy. Folosește un singur proces pentru MVP: limitarea încercărilor de login este în memorie; pentru mai multe instanțe este necesară o limitare comună și infrastructură de joburi. Procesarea fișierelor nefiabile trebuie izolată în workeri cu limite de resurse înainte de utilizare publică la scară mare.

## Testare și starea verificărilor

```bash
python -m pytest -q
python -m pip check
```

Testele folosesc fișiere Word, PDF, Excel, PowerPoint, imagini și videoclipuri reale. Verifică autentificarea, CSRF, accesul între două conturi, devizele, exporturile, FFmpeg și confirmarea de cost cu o singură execuție. Testele API folosesc **răspunsuri simulate**, nu chei sau generări plătite.

Interfața a fost verificată și într-un browser Chromium pe desktop și la 390px (dimensiune iPhone): înregistrare, login, creare proiect, export PDF și lipsa depășirii orizontale. Acesta nu este un test pe dispozitiv iPhone fizic/Safari.

În mediul cloud curent, conexiunile către OpenAI, Replicate și Crossref au returnat `ProxyError`; cheile AI lipsesc. Configurația cu domeniile și cerințele de chei a fost salvată ca draft pentru activare. **Nu este revendicată validarea reală a serviciilor externe sau publicarea în producție.**

## Structură

```text
aistent/
  __init__.py       # Configurare și application factory
  auth.py           # Conturi, sesiuni, CSRF
  db.py             # Persistență SQLite
  storage.py        # Fișiere private și validare
  workspace.py      # Proiecte, rute și confirmări AI
  exports.py        # Word, PDF, Excel, grafice
  documents.py      # Import, PowerPoint, analiză și devize
  media.py          # Pillow / FFmpeg
  ai.py             # OpenAI text, vision și imagini
  video_ai.py       # Adaptor Replicate
  research.py       # Bibliografie Crossref
  templates/        # Interfață română
  static/           # CSS, JS și favicon locale
tests/              # Teste fără apeluri plătite
run.py              # Pornire server de dezvoltare
.env.example        # Nume de configurare, fără secrete
requirements.txt
requirements-dev.txt
```

## Salvarea modificărilor în GitHub

```bash
git status
git diff
git add README.md .gitignore .env.example requirements.txt requirements-dev.txt run.py aistent tests
git commit -m "Add private projects, media tools and AI integrations"
git push origin HEAD:main
```

Dacă versiunea a fost deja comisă și publicată, nu este necesar să repeți aceste comenzi. Nu adăuga `instance/`, medii virtuale, documente personale sau chei. Pentru revizuire prin pull request, publică într-o ramură nouă cu `git push origin HEAD:feature/aistent-studio` și deschide un PR spre `main`. Nu folosi `--force` când ramura remote are alte modificări.
