"""Bibliografie verificabilă prin metadatele Crossref, fără cheie API."""
import requests


def bibliography(query):
    query = query.strip()
    if not 3 <= len(query) <= 200:
        raise ValueError('Căutarea bibliografică trebuie să aibă 3–200 de caractere.')
    try:
        response = requests.get('https://api.crossref.org/works', params={'query.bibliographic': query, 'rows': 5}, headers={'User-Agent': 'Aistent/0.2 (bibliography metadata lookup)'}, timeout=(10, 20), allow_redirects=False)
        response.raise_for_status()
        data = response.json()['message']['items']
    except (requests.RequestException, KeyError, ValueError) as error:
        raise ValueError('Registrul Crossref nu este disponibil. Nu au fost inventate referințe.') from error
    entries = []
    for item in data:
        doi = item.get('DOI', '')
        if not doi.startswith('10.') or not item.get('title'):
            continue
        authors = ', '.join(' '.join(filter(None, (author.get('given'), author.get('family')))) for author in item.get('author', []))
        dates = item.get('published', {}).get('date-parts', [[]])
        year = str(dates[0][0]) if dates and dates[0] else 'fără an'
        entries.append(f"{authors or 'Autor neprecizat'} ({year}). {item['title'][0]}. https://doi.org/{doi}")
    if not entries:
        raise ValueError('Nu au fost găsite referințe DOI pentru această căutare.')
    return '\n\n'.join(entries) + '\n\nMetadate returnate de Crossref. Verifică relevanța și conținutul lucrărilor înainte de citare. Stilul bibliografic nu este normalizat automat.'
