"""Candidate matches between our transcribed texts and The World and Japan's English documents.
Prints candidate pairs (same or close date, overlapping title words) for review; the reviewed pairs are kept in
index/worldjpn_matches.json as {our file: worldjpn url}."""
import glob, json, re, datetime, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = set('the of and between to in a an for on at by with concerning respecting regarding relating its their from as is be'.split())
def words(t): return {w for w in re.findall(r'[a-z]+', t.lower().replace('japanese', 'japan')) if w not in STOP and len(w) > 2}
def day(d):
    try: return datetime.date.fromisoformat(d) if len(d) == 10 else None
    except ValueError: return None
ours = []
for f in glob.glob(f'{ROOT}/texts/*/*/*.md'):
    fm = dict(l.split(':', 1) for l in open(f, encoding='utf-8').read().split('---')[1].strip().split('\n') if ':' in l)
    fm = {k.strip(): v.strip() for k, v in fm.items()}
    if fm.get('type') in ('list', 'statistics', 'review', 'profile', 'programme', 'report', 'summary'): continue
    ours.append((os.path.relpath(f, ROOT), fm.get('title', ''), fm.get('date', ''), fm.get('parties', '')))
wj = [d for d in json.load(open(f'{ROOT}/index/worldjpn.json')) if d['date'] < '1946']
out = []
for d in wj:
    wd, ww = day(d['date']), words(d['title_en'] or '')
    for f, t, date, parties in ours:
        od = day(date)
        if wd and od:
            if abs((wd - od).days) > 4: continue
        elif date[:7] != d['date'][:7] or not date:
            continue
        ow = words(t + ' ' + parties)
        score = len(ww & ow) / max(1, min(len(ww), len(ow)))
        out.append((round(score, 2), d['date'], date, d['title_en'] or d['title_ja'], t, f, d['url']))
out.sort(key=lambda x: (-x[0], x[1]))
json.dump(out, open(f'{ROOT}/_work/worldjpn/candidates.json', 'w'), ensure_ascii=False, indent=0)
for o in out: print(f"{o[0]:.2f} | {o[1]} / {o[2]} | WJ: {o[3][:70]} | OURS: {o[4][:70]} | {o[5].split('/')[-1][:30]}")
print(len(out), 'candidate pairs')
