"""Check every World and Japan link the site uses (HEAD requests, one at a time, politely spaced).
Writes _work/worldjpn/linkcheck.tsv (url, status); resumable."""
import json, os, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worldjpn_japan_filter import japan_related
UA = 'treaties-speeches-index/1.0 (offline archive reconciliation)'
urls = [x['url'] for x in json.load(open(f'{ROOT}/index/worldjpn.json')) if japan_related(x)]
urls += [u for v in json.load(open(f'{ROOT}/index/worldjpn_matches.json')).values() for u in v]
urls = sorted(set(urls))
out = f'{ROOT}/_work/worldjpn/linkcheck.tsv'
done = {l.split('\t')[0] for l in open(out)} if os.path.exists(out) else set()
with open(out, 'a') as f:
    for k, u in enumerate(urls):
        if u in done: continue
        status = ''
        for attempt in range(3):
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers={'User-Agent': UA}), timeout=30)
                status = str(r.status); break
            except urllib.error.HTTPError as e:
                status = str(e.code); break
            except Exception as e:
                status = 'ERR ' + type(e).__name__; time.sleep(5)
        f.write(f'{u}\t{status}\n'); f.flush()
        time.sleep(0.3)
print('checked', len(urls))
