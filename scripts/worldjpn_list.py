"""List the English-language documents linked from downloaded World and Japan (worldjpn.net) index pages.
Reads _work/worldjpn/pages/*.html (index pages only; no document pages are fetched) and writes
_work/worldjpn/english_documents.tsv / .md (all) and english_documents_pre1946.md (dated before 1946)."""
import html, os, re, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = f'{ROOT}/_work/worldjpn'
BASE = 'https://worldjpn.net/documents/indices/'
MON = {m: k + 1 for k, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
LABEL = {'docs1': 'Basic documents of modern international politics (to 1945)', 'pw': 'Prewar Japanese politics and diplomacy',
         'docs2': 'Basic documents of contemporary international politics (since 1945)',
         'JPUS': 'Japan-US relations', 'JPCH': 'Japan-China relations', 'JPTW': 'Japan-Taiwan relations',
         'JPKR': 'Japan-Korean Peninsula relations', 'JPRU': 'Japan-Russia/Soviet relations', 'JPMN': 'Japan-Mongolia relations',
         'JPSEA': 'Japan-Southeast Asia relations', 'JPSA': 'Japan-South Asia relations', 'JPPC': 'Japan-Pacific states relations',
         'JPAM': 'Japan-Americas relations', 'JPEU': 'Japan-Europe relations', 'JPME': 'Japan-Middle East relations',
         'JPAF': 'Japan-Africa relations', 'JCK': 'Japan-China-Korea relations', 'PALM': 'Pacific Islands Leaders Meetings',
         'pm': 'Prime Ministers\' speeches', 'fam': 'Foreign Ministers\' speeches', 'fim': 'Finance Ministers\' speeches',
         'em': 'Economy Ministers\' speeches', 'exdpm': 'Other speeches by Prime Ministers', 'exdfam': 'Other speeches by Foreign Ministers',
         'cm': 'Cabinet decisions and important policies', 'mt': 'Multilateral conventions', 'un': 'Japanese speeches at the UN General Assembly',
         'summit': 'G7/G8 summit documents', 'JH': 'Japan\'s history issues', 'JPSC': 'Japan security policy', 'asiajp': '"Japan in Asia" collection',
         'ticad': 'TICAD documents', 'FOIP': 'Free and Open Indo-Pacific documents'}
clean = lambda x: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()

def iso(d):
    d = clean(d)
    m = re.match(r'([A-Z][a-z]{2})\.?\s+(\d{1,2}),?\s+(\d{4})', d)
    if m and m.group(1) in MON: return f'{int(m.group(3)):04d}-{MON[m.group(1)]:02d}-{int(m.group(2)):02d}'
    if m: return f'{int(m.group(3)):04d}'   # misspelt month in the index: keep the year only
    m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', d)
    if m: return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    m = re.match(r'(\d{4})年(\d{1,2})月', d) or re.match(r'([A-Z][a-z]{2})\.?\s+(\d{4})', d)
    if m and m.group(1).isdigit(): return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}'
    if m and m.group(1) in MON: return f'{int(m.group(2)):04d}-{MON[m.group(1)]:02d}'
    m = re.search(r'(\d{4})', d)
    return m.group(1) if m else ''

docs = {}
englishtitles = {}
for fn in sorted(os.listdir(f'{D}/pages')):
    m = re.match(r'([A-Za-z0-9]+)_', fn)
    if not m or m.group(1) not in LABEL: continue
    key = m.group(1); eng = '-ENG' in fn
    titles_only = False
    page = BASE + fn.replace('_', '/', 1)
    s = re.sub(r'<!--.*?-->', '', open(f'{D}/pages/{fn}', encoding='utf-8', errors='replace').read(), flags=re.S)
    for row in re.findall(r'<TR>(.*?)</TR>', s, re.S | re.I):
        cells = re.findall(r'<TD[^>]*>(.*?)</TD>', row, re.S | re.I)
        if len(cells) < 3: continue
        e = re.search(r'<A\s+HREF="([^"]+)"[^>]*>\s*(English|英語)\s*</A>', row, re.I)
        if not e: continue
        url = urllib.parse.urljoin(page, e.group(1))
        title, date = clean(cells[0]), iso(cells[-1])
        if titles_only:
            englishtitles[url] = englishtitles.get(url) or title
            continue
        d = docs.setdefault(url, {'url': url, 'title_en': '', 'title_ja': '', 'date': date, 'indices': set()})
        d['title_en' if eng else 'title_ja'] = d['title_en' if eng else 'title_ja'] or title
        d['date'] = d['date'] or date
        d['indices'].add(LABEL[key])
for u, d in docs.items():
    if not d['title_en'] and u in englishtitles:
        d['title_en'] = englishtitles[u]
rows = sorted(docs.values(), key=lambda d: (d['date'] or '9999', d['title_en'] or d['title_ja']))
with open(f'{D}/english_documents.tsv', 'w') as f:
    f.write('date\ttitle_en\ttitle_ja\tenglish_url\tindices\n')
    for d in rows: f.write(f"{d['date']}\t{d['title_en']}\t{d['title_ja']}\t{d['url']}\t{'; '.join(sorted(d['indices']))}\n")
for name, sel in [('english_documents.md', rows), ('english_documents_pre1946.md', [d for d in rows if d['date'] and d['date'] < '1946'])]:
    with open(f'{D}/{name}', 'w') as f:
        f.write(f'# English-language documents in "The World and Japan" (worldjpn.net)\n\nFrom the index pages listed in README.md; {len(sel)} documents. '
                'English title from the site\'s English indexes (blank where none of them lists the document); original title as given in its Japanese indexes.\n\n'
                '| Date | English title | Original (Japanese index) title | English text |\n|---|---|---|---|\n')
        for d in sel:
            f.write(f"| {d['date']} | {d['title_en'].replace('|', '/')} | {d['title_ja'].replace('|', '/')} | <{d['url']}> |\n")
print(len(rows), 'documents with an English version;', sum(1 for d in rows if d['date'] and d['date'] < '1946'), 'dated before 1946;',
      sum(1 for d in rows if not d['title_en']), 'listed only in Japanese indexes;', sum(1 for d in rows if not d['date']), 'undated')

import json
json.dump([{'date': d['date'], 'title_en': d['title_en'], 'title_ja': d['title_ja'], 'url': d['url'], 'indices': sorted(d['indices'])} for d in rows],
          open(f'{ROOT}/index/worldjpn.json', 'w'), ensure_ascii=False, indent=0)
