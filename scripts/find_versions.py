"""Find texts that are the same document printed in more than one source (or issue), and write
index/versions.json: a list of groups of text files, each group one document in several printed versions.
Pairs are found by shared seven-word passages; the thresholds and exclusions below were set by reviewing the
candidate list by hand (related but different documents, and articles that merely quote a statement, are left out)."""
import collections, glob, itertools, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# pairs that share wording but are different documents (parallel notes and letters, successive protocols, etc.)
NOT_SAME = [('01-grew-note-to-hirota', '02-craigie-note-to-hirota'),
            ('01-agreement-economic-collaboration', '01-monetary-pact-japan-germany'),
            ('07-arsene-henry-letter', '09-thai-plenipotentiary-letter'), ('06-matsuoka-letter-to-french', '08-matsuoka-letter-to-thai')]
# same document, different translation or heavy editing, so below the overlap threshold
ALSO_SAME = [('contemporary-japan-1942.2/', '01-tojo-diet-speech', 'tokyo-gazette-5.9-1942.3/', '02-tojo-address-79th-diet'),
             ('contemporary-japan-1941.7/', 'joint-statement', 'tokyo-gazette-5.2-1941.8/', 'konoe-wang-joint-statement')]
docs = {}
for f in glob.glob(f'{ROOT}/texts/*/*/*.md'):
    s = open(f, encoding='utf-8').read()
    fm, body = s.split('---', 2)[1], s.split('---', 2)[2]
    if re.search(r'^type:\s*list\s*$', fm, re.M): continue
    date = (re.search(r'^date:\s*(.*)$', fm, re.M) or [None, ''])[1].strip()
    w = re.findall(r'[a-z0-9]+', re.sub(r'\[\[p\.[^\]]*\]\]|\*\[Page[^\]]*\]\*', '', body).lower())
    sh = {' '.join(w[i:i + 7]) for i in range(len(w) - 6)}
    if len(sh) > 20: docs[os.path.relpath(f, ROOT)] = (sh, date)
inv = collections.defaultdict(set)
for f, (sh, _) in docs.items():
    for x in sh: inv[x].add(f)
pair = collections.Counter()
for fs in inv.values():
    if 1 < len(fs) < 6:
        for a, b in itertools.combinations(sorted(fs), 2): pair[(a, b)] += 1
same = []
for (a, b), c in pair.items():
    hi, lo = sorted((c / len(docs[a][0]), c / len(docs[b][0])), reverse=True)
    if hi < 0.6 or lo < 0.3: continue                       # low overlap, or one text merely quotes the other
    da, db = docs[a][1], docs[b][1]
    if da[:4] and db[:4] and da[:4] != db[:4]: continue       # same wording, different year: successive documents
    if any((x in a and y in b) or (x in b and y in a) for x, y in NOT_SAME): continue
    same.append((a, b))
for d1, k1, d2, k2 in ALSO_SAME:
    a = [f for f in docs if d1 in f and k1 in f]; b = [f for f in docs if d2 in f and k2 in f]
    if len(a) == 1 and len(b) == 1: same.append((a[0], b[0]))
    else: print('ALSO_SAME not found uniquely:', d1, k1, d2, k2, a, b)
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x: x = parent[x]
    return x
for a, b in same: parent[find(a)] = find(b)
groups = collections.defaultdict(list)
for f in parent: groups[find(f)].append(f)
out = sorted(sorted(g) for g in groups.values())
json.dump(out, open(f'{ROOT}/index/versions.json', 'w'), indent=1)
print(len(out), 'groups,', sum(len(g) for g in out), 'texts')
for g in out: print('  ' + ' | '.join(x.split('/', 2)[2][:58] for x in g))
