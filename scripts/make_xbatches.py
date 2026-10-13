"""Turn a selection file (index/extra_<src>.json) into second-pass batch files _work/batches/<prefix>NN.json.
usage: make_xbatches.py <tg|cj> <prefix> <max pages per batch>"""
import json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src, prefix, maxp = sys.argv[1], sys.argv[2], int(sys.argv[3])
index = {(i['ia'], i['date']): i for i in json.load(open(f'{ROOT}/index/{src}.json'))}
items = json.load(open(f'{ROOT}/index/extra_{src}.json'))
slug = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:50]
seq = {}
for it in items:
    iss = index[(it['ia'], it['issue'])]
    # the article ends where the next index entry of the same or a higher level starts
    ents = iss['entries']
    pos = next((k for k, e in enumerate(ents) if e['n'] == it['n'] and e['title'][:30] == it['title'][:30]), None)
    depth = ents[pos]['d'] if pos is not None else 0
    later = [e['n'] for e in (ents[pos + 1:] if pos is not None else ents) if e['d'] <= depth and e['n'] is not None and e['n'] > it['n']][:1]
    if later:
        it['n_next'] = later[0]
    else:  # last article of the issue (or of the bound volume): use the page count
        out = subprocess.run(['pdfinfo', f"{ROOT}/_work/pdf/{it['ia']}/issue.pdf"], capture_output=True, text=True).stdout
        it['n_next'] = min(it['n'] + 40, int(re.search(r'Pages:\s+(\d+)', out).group(1)))
    k = seq[it['ia']] = seq.get(it['ia'], 100) + 1
    it['out'] = f"texts/{src}/{it['ia']}/{k}-{it['category']}-{slug(it['title'])}.md"
    if 'subject' in it:
        it['subject_hint_unverified'] = it.pop('subject')
batches, cur, pages = [], [], 0
for it in items:
    n = max(1, it['n_next'] - it['n'])
    if cur and pages + n > maxp:
        batches.append(cur); cur, pages = [], 0
    cur.append(it); pages += n
if cur:
    batches.append(cur)
for k, b in enumerate(batches):
    name = f'{prefix}{k + 1:02d}'
    json.dump(b, open(f'{ROOT}/_work/batches/{name}.json', 'w'), ensure_ascii=False, indent=1)
    print(name, len(b), 'items', sum(max(1, i['n_next'] - i['n']) for i in b), 'pages:', '; '.join(i['title'][:28] for i in b)[:150])
