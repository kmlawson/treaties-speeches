"""Fill pages the Claude agents could not emit (placeholders "*[Page N was not transcribed. See the scan.]*")
using the Codex CLI. Only placeholder pages are sent.

  codex_fill.py list                 show files with placeholder pages
  codex_fill.py run <substr> ...     run one Codex job per matching file (sequentially)
  codex_fill.py merge                put finished _work/fill/<id>-p<N>.md pages in place of the placeholders
"""
import glob, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = re.compile(r'^\*\[Page (\d+) was not transcribed\. See the scan\.\]\*[ \t]*$', re.M)
LABEL = 'GPT (Codex CLI)'


def jobs():
    for f in sorted(glob.glob(f'{ROOT}/texts/*/*/*.md')):
        s = open(f, encoding='utf-8').read()
        pages = [int(x) for x in PH.findall(s)]
        if pages:
            fm = dict(l.split(':', 1) for l in s.split('---')[1].strip().split('\n') if ':' in l)
            rel = os.path.relpath(f, ROOT)
            first = int(re.search(r'\[\[p\.\s*(\d+)', s).group(1))
            yield {'file': rel, 'ia': rel.split('/')[2], 'id': rel.split('/')[2] + '--' + os.path.basename(rel)[:-3],
                   'title': fm['title'].strip(), 'pages': pages, 'guess': int(fm['leaf']) + 1 + pages[0] - first, 's': s}


cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
if cmd == 'list':
    for j in jobs():
        print(j['file'], j['pages'])
elif cmd == 'run':
    tmpl = open(f'{ROOT}/scripts/codex_fill.tmpl').read()
    for j in jobs():
        if not any(a in j['file'] for a in sys.argv[2:]):
            continue
        todo = [n for n in j['pages'] if not os.path.exists(f"{ROOT}/_work/fill/{j['id']}-p{n}.md")]
        if not todo:
            continue
        prompt = (tmpl.replace('{IA}', j['ia']).replace('{TITLE}', j['title'].replace('"', "'")).replace('{FILE}', j['file'])
                  .replace('{PAGES}', ', '.join(map(str, todo))).replace('{GUESS}', str(j['guess'])).replace('{ID}', j['id']))
        log = f"{ROOT}/_work/fill/{j['id']}.log"
        r = subprocess.run(['taskpolicy', '-b', 'codex', 'exec', '-s', 'workspace-write', '--skip-git-repo-check', '-'],
                           input=prompt, text=True, cwd=ROOT, stdout=open(log, 'w'), stderr=subprocess.STDOUT)
        got = [n for n in todo if os.path.exists(f"{ROOT}/_work/fill/{j['id']}-p{n}.md")]
        print(j['file'], 'exit', r.returncode, 'pages written', got, 'missing', [n for n in todo if n not in got], flush=True)
elif cmd == 'merge':
    for j in jobs():
        s, done = j['s'], []
        for n in j['pages']:
            p = f"{ROOT}/_work/fill/{j['id']}-p{n}.md"
            if not os.path.exists(p):
                continue
            t = re.sub(r'^```\w*\n|\n```$', '', open(p, encoding='utf-8').read().strip()).strip()
            if len(t) < 20:
                continue
            s = re.sub(r'^\*\[Page %d was not transcribed\. See the scan\.\]\*[ \t]*$' % n,
                       lambda m: t + f'\n\n*[Page {n} was transcribed with {LABEL}, not Claude.]*', s, count=1, flags=re.M)
            # two columns of one page may each have left a placeholder: the fill covers the whole gap on that page
            s = re.sub(r'\n*^\*\[Page %d was not transcribed\. See the scan\.\]\*[ \t]*$' % n, '', s, flags=re.M)
            done.append(n)
        if done:
            s = re.sub(r'^(notes:.*)$', lambda k: k.group(1).rstrip() + f" | pp. {', '.join(map(str, done))} transcribed with {LABEL}.", s, count=1, flags=re.M)
            open(f"{ROOT}/{j['file']}", 'w', encoding='utf-8').write(s)
            print('merged', j['file'], done)
