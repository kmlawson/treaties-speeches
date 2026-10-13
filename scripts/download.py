"""Download the source PDF of every indexed issue from the Internet Archive into _work/pdf/<ia-id>/."""
import json, os, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
UA = "treaties-speeches-index/1.0 (offline archive reconciliation)"
files = json.load(open('_work/meta/_files.json'))
def get(id):
    pdfs = [p for p in files[id]['pdfs'] if not p[0].endswith('_text.pdf')]
    name, size = pdfs[0][0], pdfs[0][1]
    d = f'_work/pdf/{id}'; os.makedirs(d, exist_ok=True)
    out = f'{d}/issue.pdf'
    if os.path.exists(out) and os.path.getsize(out) == size: return id, 'have'
    url = f'https://archive.org/download/{urllib.parse.quote(id)}/{urllib.parse.quote(name)}'
    for k in range(8):
        if k: time.sleep(30)
        r = subprocess.run(['curl', '-sSL', '--fail', '--connect-timeout', '30', '--speed-limit', '20000', '--speed-time', '60', '-A', UA, '-C', '-', '-o', out, url])
        if os.path.exists(out) and os.path.getsize(out) == size: return id, 'ok'
    return id, 'FAILED'
with ThreadPoolExecutor(1) as ex:
    for id, st in ex.map(get, list(files)):
        print(id, st, flush=True)
