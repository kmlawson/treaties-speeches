"""Build the static site in docs/ (served by GitHub Pages) from the transcribed texts in texts/<tg|cj>/<ia>/*.md.

usage: python3 scripts/build.py
Output: docs/index.html (browse), docs/search.html (full-text search), docs/doc/<id>.html (one per text),
docs/data.js (search index). Everything is self-contained and opens from file://.
"""
import html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = f'{ROOT}/docs'
SOURCES = {'tg': 'Tokyo Gazette', 'cj': 'Contemporary Japan', 'yb': 'Year Books', 'wj': 'The World and Japan'}
# year books transcribed with Haiku agents (named in the notice at the foot of each text)
HAIKU_BOOKS = {'japan-year-book-1935', 'the-japan-year-book-1937', 'japan-year-book-1939-1940'}
# items whose scan is one file of a multi-file Internet Archive item need the file name in the page link
IA_PATH = {'japan-manchoukuo-year-book-1934': 'japan-manchoukuo-year-book-1934/Japan-Manchoukuo%20Year%20Book%201934%202'}
TYPES = {'treaty': 'Treaty', 'law': 'Law', 'speech': 'Speech', 'document': 'Document', 'programme': 'Programme',
         'report': 'Report', 'profile': 'Profile', 'summary': 'Summary', 'list': 'List', 'review': 'Review',
         'statistics': 'Statistics', 'external': 'WJ ↗'}
TYPES_PL = {'treaty': 'Treaties', 'law': 'Laws', 'speech': 'Speeches', 'document': 'Other documents', 'summary': 'Summaries of laws', 'list': 'Lists of laws promulgated',
            'programme': 'Programmes and plans', 'report': 'Reports', 'review': 'Reviews and chronologies', 'statistics': 'Statistics', 'profile': 'Profiles', 'external': 'The World and Japan ↗'}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
esc = html.escape


# ---------- loading ----------

def issue_order():
    """(source, ia, issue label) -> sort position, from the parsed index pages."""
    order = {}
    for src in SOURCES:
        if not os.path.exists(f'{ROOT}/index/{src}.json'):   # external links have no issue index
            continue
        for k, i in enumerate(json.load(open(f'{ROOT}/index/{src}.json'))):
            order[(src, i['ia'], i['date'])] = k
    return order


def issue_sortdate(label):
    m = re.search(r'(\d{4})', label)
    y = int(m.group(1)) if m else 0
    mo = next((k + 1 for k, n in enumerate(MONTHS) if n in label), 1)
    return f'{y:04d}-{mo:02d}'


def load():
    order = issue_order()
    docs = []
    problems = []
    for src in SOURCES:
        base = f'{ROOT}/texts/{src}'
        if not os.path.isdir(base):
            continue
        for ia in sorted(os.listdir(base)):
            d = f'{base}/{ia}'
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith('.md'):
                    continue
                raw = open(f'{d}/{fn}', encoding='utf-8').read()
                m = re.match(r'\s*---\n(.*?)\n---\n?(.*)', raw, re.S)
                if not m:
                    problems.append(f'{src}/{ia}/{fn}: no front matter')
                    continue
                meta = {}
                for line in m.group(1).split('\n'):
                    if ':' in line:
                        k, v = line.split(':', 1)
                        v = v.strip()
                        if len(v) > 1 and v[0] == v[-1] and v[0] in '"\'':
                            v = v[1:-1]
                        meta[k.strip().lower()] = v
                meta['body'] = m.group(2).strip()
                meta['source'] = src
                meta['ia'] = ia
                meta['file'] = f'texts/{src}/{ia}/{fn}'
                t = meta.get('type', '').lower()
                if t not in TYPES:
                    problems.append(f"{meta['file']}: type '{t}'")
                    t = 'document'
                meta['type'] = t
                for k in ('title', 'issue', 'leaf', 'pages', 'date', 'author', 'parties', 'section', 'notes', 'series', 'part', 'subject'):
                    meta.setdefault(k, '')
                if not meta['title']:
                    problems.append(f"{meta['file']}: no title")
                    meta['title'] = fn[:-3]
                if not re.fullmatch(r'\d{4}(-\d{2}(-\d{2})?)?', meta['date']):
                    if meta['date']:
                        problems.append(f"{meta['file']}: date '{meta['date']}'")
                    meta['date'] = ''
                try:
                    meta['leaf'] = int(meta['leaf'])
                except ValueError:
                    problems.append(f"{meta['file']}: leaf '{meta['leaf']}'")
                    meta['leaf'] = None
                meta['id'] = f"{src}-{slug(ia.replace('tokyo-gazette-', '').replace('contemporary-japan-', ''))}-{slug(fn[:-3])}"[:90]
                meta['ipos'] = order.get((src, ia, meta['issue']))
                if meta['ipos'] is None:
                    cands = [v for (s, i, _), v in order.items() if s == src and i == ia]
                    meta['ipos'] = min(cands) if cands else 999
                    if len(cands) != 1:
                        problems.append(f"{meta['file']}: issue '{meta['issue']}' not in index")
                meta['notes'] = clean_notes(meta['notes'])
                meta['sortdate'] = meta['date'] or issue_sortdate(meta['issue'])
                docs.append(meta)
    docs.sort(key=lambda d: (list(SOURCES).index(d['source']), d['ipos'], d['leaf'] if d['leaf'] is not None else 9999, d['file']))
    return docs, problems


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# ---------- markdown ----------

def inline(s):
    s = esc(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])', r'<em>\1</em>', s)
    s = re.sub(r'(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)', r'<em>\1</em>', s)
    s = re.sub(r'\[\^(\w+)\]', r'<sup class="fn">\1</sup>', s)
    s = s.replace('[illegible]', '<span class="illeg">[illegible]</span>')
    return s


def ia_page(ia, leaf):
    return f'https://archive.org/details/{IA_PATH.get(ia, ia)}/page/n{leaf}/mode/1up'


def render_body(doc):
    """Markdown subset -> HTML. Page markers [[p. N]] become links to the scan."""
    out = []
    first_page = None
    lines = doc['body'].split('\n')
    i = 0

    def marker(label):
        nonlocal first_page
        leaf = doc['leaf']
        m = re.match(r'\d+', label)
        if leaf is not None and m:
            if first_page is None:
                first_page = int(m.group(0))
            leaf = leaf + int(m.group(0)) - first_page
        else:
            leaf = None
        if leaf is not None and leaf >= 0:
            return f'<a class="pg" href="{ia_page(doc["ia"], leaf)}" target="_blank" title="View this page of the scan">p.&nbsp;{esc(label)}</a>'
        return f'<span class="pg">p.&nbsp;{esc(label)}</span>'

    para = []

    def flush():
        if not para:
            return
        txt = []
        for k, l in enumerate(para):
            br = l.endswith('  ') or l.endswith('\\')
            l = l.rstrip('\\').strip()
            # a page marker in the middle of a paragraph stays inline
            parts = re.split(r'\[\[p\.\s*([^\]]+?)\]\]', l)
            seg = ''
            for j, p in enumerate(parts):
                seg += marker(p) if j % 2 else inline(p)
            txt.append(seg + ('<br>' if br and k < len(para) - 1 else ''))
        cls = ' class="sig"' if all(l.endswith('  ') or l.endswith('\\') for l in para[:-1]) and len(para) > 1 else ''
        out.append(f'<p{cls}>' + '\n'.join(txt) + '</p>')
        para.clear()

    while i < len(lines):
        l = lines[i]
        s = l.strip()
        m = re.fullmatch(r'\[\[p\.\s*([^\]]+?)\]\]', s)
        if m:
            flush()
            out.append(f'<div class="pgbreak">{marker(m.group(1))}</div>')
        elif re.fullmatch(r'\*\[Page \d+ (?:was|is) [^\]]*\]\*', s):
            flush()
            out.append(f'<p class="ednote">{inline(s)}</p>')
        elif not s:
            flush()
        elif re.match(r'#{1,6}\s', s):
            flush()
            n = len(s) - len(s.lstrip('#'))
            out.append(f'<h{min(n + 1, 6)} class="h">{inline(s.lstrip("#").strip())}</h{min(n + 1, 6)}>')
        elif s.startswith('|') and i + 1 < len(lines) and re.match(r'\s*\|?[\s:|-]+\|[\s:|-]*$', lines[i + 1]):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            i -= 1
            h = '<div class="tw"><table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr></thead><tbody>'
            pcols = {k for k, c in enumerate(rows[0]) if c.strip().lower() in ('page', 'pages', 'p.')}

            def cell(k, c):
                fm = re.match(r'\d+', doc['pages'])
                fp = first_page if first_page is not None else (int(fm.group(0)) if fm else None)
                if k in pcols and doc['leaf'] is not None and fp is not None:
                    return re.sub(r'\d+', lambda m: f'<a href="{ia_page(doc["ia"], doc["leaf"] + int(m.group(0)) - fp)}" target="_blank" '
                                  f'title="View this page of the scan">{m.group(0)}</a>' if int(m.group(0)) >= fp else m.group(0), esc(c))
                return inline(c)
            for r in rows[2:]:
                h += '<tr>' + ''.join(f'<td>{cell(k, c)}</td>' for k, c in enumerate(r)) + '</tr>'
            out.append(h + '</tbody></table></div>')
        elif re.match(r'\[\^(\w+)\]:', s):
            flush()
            m = re.match(r'\[\^(\w+)\]:\s*(.*)', s)
            out.append(f'<p class="fnote"><sup>{esc(m.group(1))}</sup> {inline(m.group(2))}</p>')
        elif s.startswith('>'):
            flush()
            q = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                q.append(lines[i].strip().lstrip('>').strip())
                i += 1
            i -= 1
            out.append('<blockquote>' + ''.join(f'<p>{inline(x)}</p>' for x in ' '.join(q).split('  ') if x) + '</blockquote>')
        elif re.match(r'(-{3,}|\*{3,}|\* \* \*)$', s):
            flush()
            out.append('<hr>')
        else:
            para.append(l.rstrip('\n'))
        i += 1
    flush()
    return '\n'.join(out)


def clean_notes(n):
    """Drop the workers' running remarks about pages they could not emit: the foot-of-page notice reports the
    actual state (pages still missing, pages filled by another model) from the text itself."""
    parts = [x.strip() for x in re.split(r'\s\|\s|(?<=[.;])\s+(?=[A-Z(])', n) if x.strip()]
    keep = [x for x in parts if not re.search(r'INCOMPLETE|not transcribed|BLOCKED|cut off|SKIPPAGE|placeholder|transcribed with (GPT|Gemini)|output filter', x, re.I)]
    return ' '.join(keep)


def diff_text(body):
    """Text compared by the "Show differences" option: the document only, without its headings, footnotes and
    the notes about how pages were transcribed."""
    lines = [l for l in body.split('\n') if not re.match(r'\s*(#{1,6}\s|\[\^\w+\]:|\*\*[^*]+\*\*\s*$)', l)]   # also bold title lines
    return plain('\n'.join(lines))


def plain(body):
    t = re.sub(r'\*\[Page \d+ (?:was|is) [^\]]*\]\*', ' ', body)   # editorial notes about the transcription
    t = re.sub(r'\[\[p\.[^\]]*\]\]', ' ', t)
    t = re.sub(r'[#*_|>]|\[\^\w+\]:?', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------- pages ----------

CSS = r""":root{--bg:#fbf7f0;--fg:#2a2420;--fg-muted:#6b5f55;--fg-faint:#8a7c6c;--accent:#9c3d22;--on-accent:#fff;
--header-bg:#f2e9dc;--card-bg:#fffdf9;--card-border:#e3d8c8;--input-border:#cdbfab;--input-bg:#fffdf9;--dotted:#e2d6c5;--rule:#eadfce;
--tag-bg:#f3ebdf;--mark:#ffe3a3;--treaty:#2f6b3f;--law:#5f7d24;--speech:#2e5c86;--document:#a3472a;--programme:#a2621b;--report:#7a2f22;--profile:#74466f;--summary:#4d433a;--list:#615549;--review:#73665a;--statistics:#6a5e53;
--ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;--serif:"Source Serif 4",Georgia,"Times New Roman",serif;--r:4px}
[data-theme="dark"]{--bg:#1d1916;--fg:#ece3d6;--fg-muted:#b8aa98;--fg-faint:#8c7f70;--accent:#e39a74;--on-accent:#1d1916;
--header-bg:#26201b;--card-bg:#26201b;--card-border:#4a4038;--input-border:#5a4e44;--input-bg:#2a241f;--dotted:#43392f;--rule:#3a3129;
--tag-bg:#332b24;--mark:#6e5310}
*{margin:0;padding:0;box-sizing:border-box}
html{font-size:100%;-webkit-text-size-adjust:100%}
body{font-family:var(--serif);font-size:1rem;color:var(--fg);background:var(--bg);line-height:1.5}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:56.25rem;margin:0 auto;padding:0 1.25rem}
header{background:var(--header-bg);border-bottom:3px solid var(--accent);padding:calc(3rem + env(safe-area-inset-top,0px)) 0 1.2rem;text-align:center;box-shadow:inset 0 -1px 0 color-mix(in srgb,var(--accent) 35%,transparent)}
header h1{font-size:1.9rem;font-weight:600;margin-bottom:.3rem;letter-spacing:.01em}header h1 a{color:var(--fg)}header h1 a:hover{text-decoration:none}
header .subtitle{font-size:.95rem;color:var(--fg-muted);font-style:italic;margin-bottom:.9rem}
nav{display:flex;justify-content:center;gap:.6rem;flex-wrap:wrap}
/* line of plain text links to sister resources, set apart from the page's own buttons */
.sitelinks{display:flex;flex-wrap:wrap;justify-content:center;gap:.25rem .2rem;padding:.55rem 1rem;border-bottom:1px solid var(--rule);font-family:var(--ui);font-size:.78rem;line-height:1.5}
.sitelinks a{color:var(--fg-muted);white-space:nowrap}
.sitelinks a:hover{color:var(--accent);text-decoration:underline}
.sitelinks a:not(:last-child)::after{content:"\00b7";color:var(--fg-faint);margin-left:.45rem;display:inline-block;text-decoration:none}
.sitelinks.bottom{border-bottom:none;border-top:1px solid var(--rule);margin-top:2.5rem;padding-top:.8rem}
.sitelinks.bottom+footer{margin-top:.4rem;border-top:none}
/* one control style for every button, toggle, select and input */
.btn,nav a,.chip,.controls select,.controls input[type=search],.tools a,.tools button,.display-toolbar button{
font-family:var(--ui);font-size:.8125rem;font-weight:600;line-height:1.2;min-height:2rem;padding:.35rem .8rem;
border:1.5px solid var(--accent);border-radius:var(--r);background:var(--input-bg);color:var(--accent);
display:inline-flex;align-items:center;justify-content:center;cursor:pointer;white-space:nowrap;text-decoration:none;
transition:background .15s,color .15s;-webkit-tap-highlight-color:transparent}
nav a{font-size:.9375rem;padding:.4rem 1.1rem;background:transparent}
nav a:hover,nav a.active,.tools a:hover,.tools button:hover,.display-toolbar button:hover,.chip.on{background:var(--accent);color:var(--on-accent);text-decoration:none}
.chip{user-select:none;border-color:var(--input-border);color:var(--fg-muted);font-weight:500}
.chip:hover{border-color:var(--accent);color:var(--accent)}.chip.on:hover{color:var(--on-accent)}
.chip.on{border-color:var(--accent)}
#typeChips .chip.on,#typeChips .chip.on:hover{color:#fff}
.chiphint{font-family:var(--ui);font-size:.72rem;color:var(--fg-faint);flex-basis:100%;margin-top:-.15rem}
.chip.on[data-v=treaty]{background:var(--treaty);border-color:var(--treaty)}.chip.on[data-v=law]{background:var(--law);border-color:var(--law)}
.chip.on[data-v=speech]{background:var(--speech);border-color:var(--speech)}.chip.on[data-v=document]{background:var(--document);border-color:var(--document)}
.chip.on[data-v=list]{background:var(--list);border-color:var(--list)}
.chip.on[data-v=summary]{background:var(--summary);border-color:var(--summary)}
.chip[data-v=external]{border-radius:0}.chip.on[data-v=external]{background:var(--fg-muted);border-color:var(--fg-muted);color:#fff}
.wjlink{display:inline-block;margin-left:.45rem;padding:0 .3rem;font-family:var(--ui);font-size:.66rem;font-weight:700;line-height:1.45;letter-spacing:.03em;color:var(--fg-muted);border:1px solid var(--fg-muted);border-radius:0;white-space:nowrap;vertical-align:.08em}
.wjlink:hover{background:var(--fg-muted);color:var(--bg);text-decoration:none}
.chip.on[data-v=programme]{background:var(--programme);border-color:var(--programme)}.chip.on[data-v=report]{background:var(--report);border-color:var(--report)}.chip.on[data-v=review]{background:var(--review);border-color:var(--review)}.chip.on[data-v=statistics]{background:var(--statistics);border-color:var(--statistics)}.chip.on[data-v=profile]{background:var(--profile);border-color:var(--profile)}
.controls select,.controls input[type=search]{font-weight:400;color:var(--fg);border-color:var(--input-border);justify-content:flex-start;cursor:auto;max-width:100%}
.controls select{cursor:pointer}
.controls input[type=search]{flex:1 1 14rem;min-width:10rem;font-size:.9375rem}
.controls select:focus,.controls input:focus,.chip:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.controls{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--rule);padding:.6rem 0;margin-top:.75rem;
display:flex;gap:.5rem .9rem;flex-wrap:wrap;align-items:center}
.chips{display:flex;gap:.3rem;flex-wrap:wrap}
.loadmsg{font-family:var(--ui);font-size:.8125rem;color:var(--accent);font-weight:600}
.count{font-family:var(--ui);font-size:.8125rem;color:var(--fg-faint);margin-left:auto;white-space:nowrap}
footer{text-align:center;padding:1.5rem 0;margin-top:2.5rem;border-top:1px solid var(--dotted);font-family:var(--ui);font-size:.8125rem;color:var(--fg-faint)}
header{position:relative}
.display-toolbar{position:absolute;top:calc(.9rem + env(safe-area-inset-top,0px));right:max(.9rem,env(safe-area-inset-right,0px));display:flex;gap:.2rem}
.display-toolbar button{min-width:2rem;min-height:1.75rem;padding:.2rem .45rem;font-size:.75rem;border-color:var(--input-border);background:transparent;color:var(--fg-muted)}
.back-to-top{position:fixed;bottom:1.25rem;right:1.25rem;width:2.5rem;height:2.5rem;min-height:0;padding:0;opacity:0;pointer-events:none;
background:var(--accent);color:var(--on-accent);font-size:1.1rem;transition:opacity .3s;z-index:100}
.back-to-top.visible{opacity:.85;pointer-events:auto}
.intro{margin:1.4rem 0 .4rem;font-size:.97rem;color:var(--fg-muted)}
.volume-heading{font-size:1.25rem;color:var(--accent);border-bottom:2px solid var(--accent);padding-bottom:.35rem;margin:2.1rem 0 .9rem;scroll-margin-top:7rem}
.issue-heading{font-size:1.0625rem;margin:1.4rem 0 .25rem;scroll-margin-top:7rem;display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap}
.issue-heading .issue-num{font-family:var(--ui);font-weight:400;font-size:.8125rem}
.entry-list{list-style:none;margin:0 0 .5rem}
.entry-item{display:grid;grid-template-columns:5.25rem minmax(0,1fr) auto;gap:.1rem .7rem;align-items:baseline;padding:.3rem 0;border-bottom:1px dotted var(--dotted);line-height:1.4}
.entry-item:last-child{border-bottom:none}
.entry-text{min-width:0;overflow-wrap:anywhere}.entry-attrib{color:var(--fg-muted);font-size:.875rem;font-style:italic}
.entry-page{font-family:var(--ui);font-size:.8125rem;white-space:nowrap;color:var(--fg-faint)}
/* type labels: fixed-width box sized for the longest label, never wrapping or overflowing */
.tag{display:inline-block;box-sizing:border-box;width:5.25rem;padding:.16rem 0;text-align:center;font-family:var(--ui);font-size:.625rem;font-weight:700;line-height:1.3;
letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;overflow:hidden;border-radius:var(--r);border:none;color:#fff;background:var(--list);vertical-align:middle}
.tag.treaty{background:var(--treaty)}.tag.law{background:var(--law)}.tag.speech{background:var(--speech)}.tag.document{background:var(--document)}.tag.summary{background:var(--summary)}.tag.list{background:var(--list)}.tag.programme{background:var(--programme)}.tag.report{background:var(--report)}.tag.review{background:var(--review)}.tag.statistics{background:var(--statistics)}.tag.external{background:transparent;color:var(--fg-muted);border:1.5px solid var(--fg-muted);border-radius:0;padding:.06rem 0}.tag.profile{background:var(--profile)}
.hidden{display:none!important}
/* document page */
.doc-head{margin:1.6rem 0 1.1rem;padding-bottom:.9rem;border-bottom:1px solid var(--rule)}
.doc-head h2{font-size:1.5rem;line-height:1.25;margin:.5rem 0 .6rem;overflow-wrap:anywhere}
.meta{font-family:var(--ui);font-size:.84rem;display:grid;grid-template-columns:max-content minmax(0,1fr);gap:.2rem .9rem}
.meta dt{color:var(--fg-faint)}.meta dd{color:var(--fg);overflow-wrap:anywhere}
.note{max-width:43.75rem;margin:2rem auto 0;font-family:var(--ui);font-size:.84rem;line-height:1.5;color:var(--fg-muted);border:1.5px solid var(--input-border);border-radius:var(--r);background:var(--input-bg)}
.note summary{cursor:pointer;padding:.45rem .9rem;font-weight:600;color:var(--accent);list-style-position:inside}
.note summary:hover{background:var(--tag-bg)}.note[open] summary{border-bottom:1px solid var(--rule)}
.note p{padding:.6rem .9rem;margin:0;overflow-wrap:anywhere}
.note+.disclaimer{margin-top:.75rem}
.disclaimer{max-width:43.75rem;margin:2rem auto 0;padding:.7rem .9rem;border:1.5px solid var(--input-border);border-left:4px solid var(--accent);border-radius:var(--r);font-family:var(--ui);font-size:.84rem;line-height:1.5;color:var(--fg-muted);background:var(--tag-bg)}
.series{margin:0 auto 1.2rem;max-width:43.75rem;font-family:var(--ui);font-size:.84rem;color:var(--fg-muted);display:flex;flex-wrap:wrap;gap:.35rem;align-items:center}
.series strong{color:var(--fg)}.series .btn{min-height:1.75rem;padding:.15rem .55rem}.series .btn.on{background:var(--accent);color:var(--on-accent)}
.parthead{max-width:43.75rem;margin:2.2rem auto .8rem;padding-top:.8rem;border-top:2px solid var(--accent);font-size:1.15rem}
.parthead small{display:block;font-family:var(--ui);font-weight:400;font-size:.78rem;color:var(--fg-faint)}
.versions{margin:0 auto 1rem;max-width:43.75rem;font-family:var(--ui);font-size:.84rem;color:var(--fg-muted);display:flex;flex-wrap:wrap;gap:.35rem;align-items:center}
.versions span{flex-basis:100%;margin-bottom:.1rem}.versions .btn{min-height:1.75rem;padding:.15rem .6rem;font-weight:500}.versions .btn.on{background:var(--accent);color:var(--on-accent)}
.diffbar{max-width:43.75rem;margin:-.6rem auto 1.2rem;font-family:var(--ui);font-size:.84rem;color:var(--fg-muted);display:flex;flex-wrap:wrap;gap:.3rem .8rem;align-items:center}
.diffbar label{cursor:pointer;display:inline-flex;gap:.4rem;align-items:center;color:var(--fg)}.diffbar input{accent-color:var(--accent);width:1rem;height:1rem}
.difflegend{flex-basis:100%;font-size:.78rem}
mark.d-chg{background:color-mix(in srgb,var(--document) 22%,transparent);color:inherit;border-bottom:1.5px solid var(--document);padding:0 1px}
.d-ins,.d-ins-key{font-family:var(--ui);font-size:.8em;color:var(--treaty);background:color-mix(in srgb,var(--treaty) 12%,transparent);border-radius:3px;padding:0 .25em}
details.d-ins-long{display:inline;font-family:var(--ui);font-size:.8em;color:var(--treaty);background:color-mix(in srgb,var(--treaty) 10%,transparent);border-radius:3px;padding:0 .3em}
details.d-ins-long summary{display:inline;cursor:pointer;font-weight:600}details.d-ins-long[open]{display:block;margin:.3em 0;padding:.4em .6em;font-family:var(--serif);font-size:.95em;color:var(--fg)}
details.d-ins-long[open] summary{display:block;font-family:var(--ui);font-size:.8em;color:var(--treaty);margin-bottom:.2em}
.tools{margin-top:.8rem;display:flex;gap:.5rem;flex-wrap:wrap}
.doc{font-size:1.09rem;line-height:1.62;max-width:43.75rem;margin:0 auto;overflow-wrap:break-word}
.doc p{margin:0 0 .85em}
.doc p.sig{text-align:right;font-size:.95em}
.doc .h{text-align:center;font-size:1em;letter-spacing:.05em;margin:1.6em 0 .8em;font-weight:bold}
.doc h3.h{font-size:1.1em}.doc h4.h{font-variant:small-caps;letter-spacing:.06em}.doc h5.h,.doc h6.h{font-style:italic;font-weight:normal;letter-spacing:0}
.doc blockquote{margin:0 0 .85em 1.6em;font-size:.95em}
.doc hr{border:none;border-top:1px solid var(--dotted);width:30%;margin:1.5em auto}
.pgbreak{text-align:right;margin:1.2em 0 .5em;border-top:1px dotted var(--dotted);padding-top:.1rem;line-height:1.2}
.pg{font-family:var(--ui);font-size:.75rem;color:var(--fg-faint)}a.pg{color:var(--accent)}
p .pg{margin:0 .25rem;padding:0 .25rem;border:1px dotted var(--dotted);border-radius:var(--r)}
.illeg{color:#b00020;font-style:italic}.doc p.ednote{font-family:var(--ui);font-size:.78rem;color:var(--fg-faint)}.fnote{font-size:.85em;color:var(--fg-muted)}sup.fn{font-size:.7em}
.tw{overflow-x:auto;margin:0 0 1em}table{border-collapse:collapse;font-family:var(--ui);font-size:.84rem;margin:0 auto}
th,td{border:1px solid var(--card-border);padding:.25rem .55rem;text-align:left;vertical-align:top}th{background:var(--header-bg)}
.pn{display:flex;justify-content:space-between;gap:1.25rem;margin:2.1rem 0 0;padding-top:.9rem;border-top:1px solid var(--rule);font-size:.9rem}
.pn a{flex:1;min-width:0;overflow-wrap:anywhere}.pn a:last-child{text-align:right}
.pn small{display:block;font-family:var(--ui);color:var(--fg-faint);font-size:.75rem}
/* search */
.result{padding:.75rem 0;border-bottom:1px dotted var(--dotted)}
.result h3{font-size:1.0625rem;font-weight:normal;margin-bottom:.15rem;display:grid;grid-template-columns:5.25rem minmax(0,1fr);gap:.7rem;align-items:baseline}
.result .rmeta,.result .snip{margin-left:5.95rem}
.result .rmeta{font-family:var(--ui);font-size:.78rem;color:var(--fg-muted)}
.result .snip{font-size:.94rem;color:var(--fg-muted);margin-top:.25rem;overflow-wrap:anywhere}
mark{background:var(--mark);color:inherit;padding:0 1px}
.hint{font-family:var(--ui);color:var(--fg-faint);font-size:.84rem;margin:.9rem 0}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;align-items:center;justify-content:center;padding:1rem}
.modal.open{display:flex}.modal-inner{background:var(--card-bg);max-width:40rem;max-height:86vh;overflow:auto;padding:1.6rem 1.75rem;border-radius:calc(var(--r) + 2px);font-size:.97rem}
.modal-inner h2{font-size:1.25rem;margin-bottom:.6rem}.modal-inner p{margin-bottom:.8em}
.modal-inner .btn{float:right;min-width:2rem;padding:.2rem .5rem;margin:0 0 .5rem .75rem}
@media (max-width:600px){header h1{font-size:1.25rem}.container{padding:0 .9rem}.doc{font-size:1.03rem}
.entry-item{grid-template-columns:5.25rem minmax(0,1fr)}.entry-page{grid-column:2}
.result .rmeta,.result .snip{margin-left:0}.count{margin-left:0}
.display-toolbar{position:static;justify-content:center;margin-top:.7rem}.sitelinks{padding:.4rem .6rem}.back-to-top{bottom:.9rem;right:.9rem}}
@media print{.sitelinks,header nav,.display-toolbar,.back-to-top,.pn,.tools,.controls{display:none}.doc{font-size:12pt}}
"""

COMMON_JS = r"""(function(){var r=document.documentElement,k='ts-theme',f='ts-font';
try{var t=localStorage.getItem(k);if(t)r.setAttribute('data-theme',t);var z=localStorage.getItem(f);if(z&&+z>=70&&+z<=180)r.style.fontSize=(+z)+'%'}catch(e){}
window.addEventListener('DOMContentLoaded',function(){
var b=document.getElementById('themeBtn');if(b)b.onclick=function(){var d=r.getAttribute('data-theme')=='dark'?'light':'dark';r.setAttribute('data-theme',d);try{localStorage.setItem(k,d)}catch(e){}};
function fs(d){var c=parseInt(r.style.fontSize)||100;c=Math.max(70,Math.min(180,c+d));r.style.fontSize=c+'%';try{localStorage.setItem(f,c)}catch(e){}}
var p=document.getElementById('fontUp'),m=document.getElementById('fontDown');if(p)p.onclick=function(){fs(10)};if(m)m.onclick=function(){fs(-10)};
var top=document.getElementById('backToTop');if(top){window.addEventListener('scroll',function(){top.classList.toggle('visible',window.scrollY>400)});top.onclick=function(){window.scrollTo({top:0,behavior:'smooth'})}}
var mo=document.getElementById('aboutModal'),na=document.getElementById('navAbout');
if(mo&&na){na.onclick=function(e){e.preventDefault();mo.classList.add('open')};mo.onclick=function(e){if(e.target==mo||e.target.id=='aboutClose')mo.classList.remove('open')};
document.addEventListener('keydown',function(e){if(e.key=='Escape')mo.classList.remove('open')})}
});})();"""

ABOUT = """<h2>About this collection</h2>
<p>This site gathers the verbatim texts of treaties, laws, speeches and other official documents printed in two
English-language periodicals published in wartime Japan: the <em>Tokyo Gazette</em> (1937&ndash;1942), a monthly digest
of government reports issued under the supervision of the Cabinet Information Bureau, and <em>Contemporary Japan: A Review
of Far Eastern Affairs</em> (issues of 1941&ndash;1945), published by the Foreign Affairs Association of Japan, whose
&ldquo;Documentary Material&rdquo; section reprinted official texts.</p>
<p>It also includes the &ldquo;Texts of Treaties, Agreements, Notes and Statutes of the Powers Concerning Manchuria&rdquo;
(1895&ndash;1932) printed as Supplement III of the <em>Japan-Manchoukuo Year Book 1934</em> (the first of a section of texts from year books), and, from the two periodicals,
selected government programmes, reports, statistical articles, chronologies and profiles of public figures.</p>
<p>Only texts printed in full in the journals are included; commentary, summaries and articles about them are not.
The issues covered are those indexed on the <a href="https://froginawell.net/tokyo-gazette/">Tokyo Gazette table of contents</a> and
<a href="https://froginawell.net/frog/sources/primary-source-nuggets/contemporary-japan/">Contemporary Japan</a> pages at Frog in a Well,
and scanned on the Internet Archive.</p>
<p>These are official translations and statements of the wartime Japanese state and its allies, and should be read as such.</p>
<p><strong>Transcription.</strong> The texts were transcribed from the page scans by AI models (Claude Opus 5.5, Claude Sonnet 5.5 and, for the Japan Year Books, Claude Haiku 5.5;
the model used is named at the foot of each text) reading the page images, and have not been proofread by a person. Original spelling and romanisation are kept. Page numbers in the margin link to the page
of the scan on the Internet Archive: check the scan before quoting.</p>"""


SITELINKS = [
    ('Tokyo Gazette index', 'https://froginawell.net/tokyo-gazette/'),
    ('Contemporary Japan index', 'https://froginawell.net/frog/sources/primary-source-nuggets/contemporary-japan/'),
    ('The Japan Magazine index', 'https://froginawell.net/indexes/japan-magazine/'),
    ('Old Year Book Tables', 'https://froginawell.net/reference/old-tables/'),
    ('Japan Internal Affairs 1930\u20131949', 'https://froginawell.net/reference/japan-internal-affairs/'),
    ('Occupation Summations 1945\u20131948', 'https://froginawell.net/reference/summations/'),
    ('Chronicles of the Japanese Empire', 'https://froginawell.net/reference/empire-chronicle/'),
    ('Sources: Modern Japan', 'https://froginawell.net/reference/modern-japan/'),
    ('Sources: Modern Korea', 'https://froginawell.net/frog/sources/primary-sources-modern-korean-history/'),
    ('Sources: Taiwan', 'https://froginawell.net/frog/sources/primary-sources-history-of-taiwan/'),
    ('All Frog in a Well resources', 'https://froginawell.net/frog/sources/'),
]

def page(title, subtitle, active, body, depth=0, extra_head='', scripts=''):
    sitelinks = ''.join(f'<a href="{u}">{esc(t)}</a>' for t, u in SITELINKS)
    up = '../' * depth
    nav = ''.join(f'<a href="{up}{h}"{" class=active" if a == active else ""}>{t}</a>' for a, h, t in
                  [('browse', 'index.html', 'Browse'), ('search', 'search.html', 'Search')])
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap">
<link rel="stylesheet" href="{up}style.css"><script src="{up}common.js"></script>{extra_head}
</head><body>
<header><div class="container"><h1><a href="{up}index.html">Treaties, Laws and Speeches</a></h1>
<div class="subtitle">{subtitle}</div>
<nav>{nav}<a href="#" id="navAbout">About</a></nav></div>
<div class="display-toolbar"><button id="fontDown" title="Smaller text" aria-label="Smaller text">A&minus;</button><button id="fontUp" title="Larger text" aria-label="Larger text">A+</button><button id="themeBtn" title="Light / dark" aria-label="Light or dark theme">&#9680;</button></div></header>
<div class="sitelinks" role="navigation" aria-label="Related resources on Frog in a Well">{sitelinks}</div>
<div class="container">
{body}
</div>
<div class="sitelinks bottom" role="navigation" aria-label="Related resources on Frog in a Well">{sitelinks}</div>
<footer><div class="container">Texts from the <em>Tokyo Gazette</em>, <em>Contemporary Japan</em> and year books of the Japanese empire &middot;
<a href="https://froginawell.net/">Frog in a Well</a></div></footer>
<div class="modal" id="aboutModal"><div class="modal-inner"><button class="btn" id="aboutClose" aria-label="Close">&times;</button>{ABOUT}</div></div>
<button class="btn back-to-top" id="backToTop" title="Back to top">&uarr;</button>
{scripts}
</body></html>"""


def fmt_date(d):
    if not d:
        return ''
    p = d.split('-')
    if len(p) == 3:
        return f'{int(p[2])} {MONTHS[int(p[1]) - 1]} {p[0]}'
    if len(p) == 2:
        return f'{MONTHS[int(p[1]) - 1]} {p[0]}'
    return d


def who(d):
    return d['author'] or d['parties'].replace(';', ' – ').replace('  ', ' ')


def entry(d, up=''):
    if d['type'] == 'external':
        orig = (f' <span class="entry-attrib">({esc(d["title_ja"])})</span>'
                if d['title_ja'] and d['title_ja'] != d['title'] else '')
        return (f'<li class="entry-item" data-type="external" data-src="wj" data-date="{d["sortdate"]}">'
                f'<span class="tag external">{TYPES["external"]}</span>'
                f'<span class="entry-text"><a href="{esc(d["url"])}" target="_blank" rel="noopener" title="English text on The World and Japan (worldjpn.net)">{esc(d["title"])}</a>{orig}</span>'
                f'<span class="entry-page">{esc(fmt_date(d["date"]))}</span></li>')
    w = who(d)
    att = f' <span class="entry-attrib">({esc(w)})</span>' if w and w.lower() not in d['title'].lower() else ''
    if d.get('sn'):
        att += f' <span class="entry-attrib">&middot; part {d["sk"]} of {d["sn"]}</span>'
    if d.get('vers'):
        att += f' <span class="entry-attrib">&middot; {len(d["vers"])} printed versions</span>'
    return (f'<li class="entry-item" data-type="{d["type"]}" data-src="{d["source"]}" data-date="{d["sortdate"]}">'
            f'<span class="tag {d["type"]}">{TYPES[d["type"]]}</span>'
            f'<span class="entry-text"><a href="{up}doc/{d["id"]}.html">{esc(d["title"])}</a>{att}'
            + ''.join(f' <a class="wjlink" href="{esc(u)}" target="_blank" rel="noopener" title="English text of this document on The World and Japan (worldjpn.net)">WJ&nbsp;↗</a>' for u in d.get('wj', [])[:1])
            + '</span>'
            f'<span class="entry-page">{esc(fmt_date(d["date"]))}</span></li>')


def build():
    docs, problems = load()
    OPUS = json.load(open(f'{ROOT}/index/opus_files.json')) if os.path.exists(f'{ROOT}/index/opus_files.json') else {}
    ids = {}
    for d in docs:
        if d['id'] in ids:
            n = 2
            while f"{d['id']}-{n}" in ids:
                n += 1
            d['id'] = f"{d['id']}-{n}"
        ids[d['id']] = d
    series = {}
    for d in docs:
        if d['series']:
            series.setdefault((d['source'], d['series']), []).append(d)
    series = {k: v for k, v in series.items() if len(v) > 1}
    for key, parts in series.items():
        parts.sort(key=lambda d: (int(d['part']) if d['part'].isdigit() else 999, d['ipos'], d['file']))
        for k, d in enumerate(parts):
            d['sk'], d['sn'], d['sslug'] = k + 1, len(parts), f"{key[0]}-{slug(key[1])}"
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(f'{SITE}/doc')
    os.makedirs(f'{SITE}/series')
    open(f'{SITE}/.nojekyll', 'w').write('')
    open(f'{SITE}/style.css', 'w').write(CSS)
    open(f'{SITE}/common.js', 'w').write(COMMON_JS)
    matches = json.load(open(f'{ROOT}/index/worldjpn_matches.json')) if os.path.exists(f'{ROOT}/index/worldjpn_matches.json') else {}
    for d in docs:
        d['wj'] = matches.get(d['file'], [])
    # the same document printed in several sources: one entry in the lists (the longest version), all versions
    # reachable from each other on their own pages
    byfile = {d['file']: d for d in docs}
    for g in (json.load(open(f'{ROOT}/index/versions.json')) if os.path.exists(f'{ROOT}/index/versions.json') else []):
        members = [byfile[f] for f in g if f in byfile]
        if len(members) < 2:
            continue
        words = lambda d: len(re.sub(r'\*\[Page \d+ was not transcribed[^\]]*\]\*', '', d['body']).split())
        members.sort(key=lambda d: (-words(d), list(SOURCES).index(d['source']), d['ipos']))
        for d in members:
            d['vers'] = members
        for d in members[1:]:
            d['secondary'] = True
        if not members[0]['wj']:
            members[0]['wj'] = next((d['wj'] for d in members if d['wj']), [])
    listed = [d for d in docs if not d.get('secondary')]
    absorbed = {u for v in matches.values() for u in v}
    externals = []
    for x in (json.load(open(f'{ROOT}/index/worldjpn.json')) if os.path.exists(f'{ROOT}/index/worldjpn.json') else []):
        if x['url'] in absorbed:
            continue
        externals.append({'type': 'external', 'source': 'wj', 'title': x['title_en'] or x['title_ja'], 'title_ja': x['title_ja'] if x['title_en'] else '',
                          'url': x['url'], 'date': x['date'], 'sortdate': x['date'], 'file': x['url'], 'id': ''})
    counts = {t: sum(1 for d in listed + externals if d['type'] == t) for t in TYPES}
    postwar = [x for x in externals if x['sortdate'] >= '1946']        # loaded only when "All years" is chosen
    externals = [x for x in externals if x['sortdate'] < '1946']
    sub = ('Texts from the <em>Tokyo Gazette</em>, <em>Contemporary Japan</em> and year books of the Japanese empire'
           if any(d['source'] == 'yb' for d in docs) else 'Verbatim texts from the <em>Tokyo Gazette</em> and <em>Contemporary Japan</em>, 1937&ndash;1945')

    # ---- post-war external links, a separate file loaded on demand by the browse and search pages
    open(f'{SITE}/wj_postwar.js', 'w').write('window.WJPOST=' + json.dumps(
        [{'t': x['title'], 'j': x['title_ja'], 'u': x['url'], 'd': fmt_date(x['date']), 'o': x['sortdate']}
         for x in sorted(postwar, key=lambda x: (x['sortdate'], x['title']))], ensure_ascii=False, separators=(',', ':')) + ';')

    # ---- browse
    b = [f'<p class="intro">{len(listed)} texts printed in English-language periodicals and year books of 1930s&ndash;40s Japan: '
         + ', '.join(f'{counts[t]} {TYPES_PL[t].lower()}' for t in TYPES if counts[t] and t != 'external') + '. Each links to the page of the original scan.</p>']
    b.append('<p class="intro">The best open access resource online for documents related to the history of Japanese foreign policy is '
             '<a href="https://worldjpn.net/iefindex.html">The World and Japan</a> by Professor Tanaka Akihito and the National Graduate '
             'Institute for Policy Studies (GRIPS). In addition to a wealth of databases and Japanese language documents it also provides access '
             'to many English, Chinese, and Korean versions of these documents. In addition to the scanned versions below links have been added '
             'to that resource for documents available there in English.</p>')
    b.append('<p class="intro"><strong>Important:</strong> The scanned documents are taken verbatim from the published source and, in addition to '
             'possible extraction errors, may not exactly match the official diplomatic record. If you intend to cite these documents, compare '
             'with the original source but also seek out official versions.</p>')
    b.append('<div class="controls"><div class="chips" id="typeChips">'
             + ''.join(f'<span class="chip on" data-v="{t}">{TYPES_PL[t]}</span>' for t in TYPES if counts[t]) + '<span class="chip" data-all="1" title="Show every category">Show all</span><span class="chiphint">Click a category to hide or show it. Option-click (Alt-click on Windows) to show only that one.</span></div>'
             '<div class="chips" id="srcChips">' + ''.join(f'<span class="chip on" data-v="{s}">{n}</span>' for s, n in SOURCES.items()) + '</div>'
             '<div class="chips" id="eraChips" title="Most of The World and Japan\'s documents are post-war"><span class="chip on" data-v="pre">Up to 1945</span><span class="chip" data-v="all">All years</span></div>'
             '<div class="chips" id="viewChips"><span class="chip on" data-v="issue">By issue</span><span class="chip" data-v="date">By date</span></div>'
             '<select id="jumpSelect"><option value="">&mdash; Jump to an issue &mdash;</option></select>'
             '<select id="yearSelect" class="hidden"><option value="">&mdash; Jump to a year &mdash;</option></select>'
             '<span class="loadmsg hidden" id="loadmsg"></span><span class="count" id="count"></span></div>')
    b.append('<div id="byIssue">')
    cur_src = cur_issue = None
    for d in listed:
        if d['source'] != cur_src:
            if cur_issue is not None:
                b.append('</ul></section>')
            if cur_src is not None:
                b.append('</section>')
            cur_src = d['source']
            cur_issue = None
            b.append(f'<section class="src" data-src="{cur_src}"><h2 class="volume-heading" id="{cur_src}">{SOURCES[cur_src]}</h2>')
        key = (d['ia'], d['issue'])
        if key != cur_issue:
            if cur_issue is not None:
                b.append('</ul></section>')
            cur_issue = key
            iid = f"{d['source']}-{d['ipos']}"
            b.append(f'<section class="iss" id="{iid}" data-label="{esc(SOURCES[cur_src])} &mdash; {esc(d["issue"])}">'
                     f'<h3 class="issue-heading">{esc(d["issue"])}<a class="issue-num" href="https://archive.org/details/{IA_PATH.get(d["ia"], d["ia"])}" target="_blank">scan &rarr;</a></h3><ul class="entry-list">')
        b.append(entry(d))
    if listed:
        b.append('</ul></section></section>')
    if externals:
        b.append('<section class="src" data-src="wj"><h2 class="volume-heading" id="wj">The World and Japan</h2>'
                 '<section class="iss" id="wj-0" data-label="The World and Japan &mdash; English documents (external links)">'
                 '<h3 class="issue-heading">English documents on worldjpn.net<a class="issue-num" href="https://worldjpn.net/iefindex.html" target="_blank">site &rarr;</a></h3><ul class="entry-list">')
        for x in sorted(externals, key=lambda x: (x['sortdate'], x['title'])):
            b.append(entry(x))
        b.append('</ul></section></section>')
    b.append('</div><div id="byDate" class="hidden">')
    year = None
    for d in sorted(listed + externals, key=lambda d: (d['sortdate'], d['file'])):
        y = d['sortdate'][:4]
        if y != year:
            if year:
                b.append('</ul></section>')
            year = y
            b.append(f'<section class="iss yr" id="y-{y}" data-year="{y}"><h2 class="volume-heading">{y}</h2><ul class="entry-list">')
        b.append(entry(d))
    if docs:
        b.append('</ul></section>')
    b.append('</div>')
    js = r"""<script>(function(){
var on={type:{},src:{}};function chips(id,k,multi){var c=document.getElementById(id);[].forEach.call(c.children,function(x){if(multi&&x.dataset.v)on[k][x.dataset.v]=true;
x.onclick=function(ev){if(multi){var kids=[].filter.call(c.children,function(y){return y.dataset.v});
if(x.dataset.all){kids.forEach(function(y){y.classList.add('on');on[k][y.dataset.v]=true})}
else if(ev.altKey){kids.forEach(function(y){y.classList.toggle('on',y==x);on[k][y.dataset.v]=y==x})}
else{x.classList.toggle('on');on[k][x.dataset.v]=x.classList.contains('on');
if(!kids.some(function(y){return y.classList.contains('on')})){kids.forEach(function(y){y.classList.add('on');on[k][y.dataset.v]=true})}}}
else{[].forEach.call(c.children,function(y){y.classList.toggle('on',y==x)});
document.getElementById('byIssue').classList.toggle('hidden',x.dataset.v!='issue');document.getElementById('byDate').classList.toggle('hidden',x.dataset.v!='date');
document.getElementById('jumpSelect').classList.toggle('hidden',x.dataset.v!='issue');document.getElementById('yearSelect').classList.toggle('hidden',x.dataset.v!='date')}
apply()}})}
var era='pre',loaded=false,loading=false,msg=document.getElementById('loadmsg');
function esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function li(e){return '<li class="entry-item" data-type="external" data-src="wj" data-date="'+e.o+'"><span class="tag external">WJ \u2197</span><span class="entry-text"><a href="'+esc(e.u)+'" target="_blank" rel="noopener" title="English text on The World and Japan (worldjpn.net)">'+esc(e.t)+'</a>'+(e.j?' <span class="entry-attrib">('+esc(e.j)+')</span>':'')+'</span><span class="entry-page">'+esc(e.d)+'</span></li>'}
function loadPost(done){if(loaded)return done();if(loading)return;loading=true;msg.classList.remove('hidden');msg.textContent='Loading post-war links\u2026';
var sc=document.createElement('script');sc.src='wj_postwar.js';sc.onerror=function(){msg.textContent='Could not load the post-war links.';loading=false};
sc.onload=function(){var L=window.WJPOST||[],k=0,wjl=document.querySelector('#wj-0 .entry-list'),bd=document.getElementById('byDate'),ys=document.getElementById('yearSelect');
(function step(){var end=Math.min(L.length,k+200),a='',byY={};for(;k<end;k++){var e=L[k],h=li(e);a+=h;var y=e.o.slice(0,4);(byY[y]=byY[y]||[]).push(h)}
if(wjl)wjl.insertAdjacentHTML('beforeend',a);Object.keys(byY).sort().forEach(function(y){var sec=document.getElementById('y-'+y);
if(!sec){bd.insertAdjacentHTML('beforeend','<section class="iss yr" id="y-'+y+'" data-year="'+y+'"><h2 class="volume-heading">'+y+'</h2><ul class="entry-list"></ul></section>');sec=document.getElementById('y-'+y);
var o=document.createElement('option');o.value='y-'+y;o.textContent=y;ys.appendChild(o)}sec.querySelector('.entry-list').insertAdjacentHTML('beforeend',byY[y].join(''))});
msg.textContent='Loading post-war links\u2026 '+Math.round(100*k/L.length)+'%';
if(k<L.length)setTimeout(step,0);else{loaded=true;loading=false;msg.classList.add('hidden');done()}})()};document.body.appendChild(sc)}
[].forEach.call(document.getElementById('eraChips').children,function(x){x.onclick=function(){var v=x.dataset.v;
[].forEach.call(x.parentNode.children,function(y){y.classList.toggle('on',y==x)});if(v=='all'&&!loaded){loadPost(function(){era='all';apply()})}else{era=v;apply()}}});
function apply(){var n=0,vis=document.getElementById('byIssue').classList.contains('hidden')?'byDate':'byIssue';
var x=0;[].forEach.call(document.querySelectorAll('.entry-item'),function(li){var s=on.type[li.dataset.type]&&on.src[li.dataset.src]&&(era=='all'||li.dataset.date<'1946');li.classList.toggle('hidden',!s);if(s&&li.closest('#'+vis)){if(li.dataset.type=='external')x++;else n++}});
[].forEach.call(document.querySelectorAll('.iss,.src'),function(s){s.classList.toggle('hidden',!s.querySelector('.entry-item:not(.hidden)'))});
document.getElementById('count').textContent=n+' transcribed document'+(n==1?'':'s')+' \u00b7 '+x+' external link'+(x==1?'':'s');
[].forEach.call(document.querySelectorAll('#yearSelect option, #jumpSelect option'),function(o){if(!o.value)return;var t=document.getElementById(o.value);o.hidden=!!(t&&t.classList.contains('hidden'))})}
chips('typeChips','type',true);chips('srcChips','src',true);chips('viewChips','view',false);
var sel=document.getElementById('jumpSelect');[].forEach.call(document.querySelectorAll('#byIssue .iss'),function(s){var o=document.createElement('option');o.value=s.id;o.innerHTML=s.dataset.label;sel.appendChild(o)});
sel.onchange=function(){if(this.value)document.getElementById(this.value).scrollIntoView({behavior:'smooth',block:'start'})};
var ys=document.getElementById('yearSelect');[].forEach.call(document.querySelectorAll('#byDate .yr'),function(s){var o=document.createElement('option');o.value=s.id;o.textContent=s.dataset.year;ys.appendChild(o)});
ys.onchange=sel.onchange;apply()})();</script>"""
    open(f'{SITE}/index.html', 'w').write(page('Treaties, Laws and Speeches — Tokyo Gazette & Contemporary Japan', sub, 'browse', '\n'.join(b), scripts=js))

    # ---- documents
    for k, d in enumerate(docs):
        rows = [('Type', TYPES[d['type']]), ('Date', fmt_date(d['date'])),
                ('Speaker / issued by' if d['type'] in ('speech', 'document') else 'Author', d['author']),
                ('Parties', d['parties'].replace(';', ' · ')), ('Printed in', (f"<em>{esc(d['issue'])}</em>" if d['source'] == 'yb' else f"<em>{SOURCES[d['source']]}</em>, {esc(d['issue'])}")
                 + (f", pp.&nbsp;{esc(d['pages'])}" if re.search(r'\D', d['pages']) else (f", p.&nbsp;{esc(d['pages'])}" if d['pages'] else ''))),
                ('Subject', d['subject']), ('Section', d['section']), ('Part', f"{d['sk']} of {d['sn']} of {d['series']}" if d.get('sn') else '')]
        scan = ia_page(d['ia'], d['leaf']) if d['leaf'] is not None else f"https://archive.org/details/{IA_PATH.get(d['ia'], d['ia'])}"
        meta = ''.join(f'<dt>{a}</dt><dd>{v if a == "Printed in" else esc(v)}</dd>' for a, v in rows if v)
        cite = f"“{d['title']},” {d['issue'] if d['source'] == 'yb' else SOURCES[d['source']] + ' (' + d['issue'] + ')'}{': ' + d['pages'] if d['pages'] else ''}."
        h = [f'<div class="doc-head"><span class="tag {d["type"]}">{TYPES[d["type"]]}</span><h2>{esc(d["title"])}</h2><dl class="meta">{meta}</dl>']
        h.append(f'<div class="tools"><a href="{scan}" target="_blank">View the scan on the Internet Archive &rarr;</a>'
                 + ''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener" title="English text of this document on The World and Japan (worldjpn.net)">The World and Japan &#8599;</a>' for u in d['wj'][:1]) +
                 f'<button id="citeBtn" data-cite="{esc(cite)}">Copy citation</button><button id="textBtn">Copy text</button></div></div>')
        if d.get('vers'):
            lab = lambda x: (f'<em>{esc(x["issue"])}</em>' if x['source'] == 'yb' else f'<em>{SOURCES[x["source"]]}</em>, {esc(x["issue"])}')
            h.append('<nav class="versions"><span>This document was printed in more than one place. Versions:</span>'
                     + ''.join(f'<a class="btn{" on" if x is d else ""}" href="{x["id"]}.html">{lab(x)}{" (fullest)" if k == 0 else ""}</a>'
                               for k, x in enumerate(d['vers'])) + '</nav>')
            others = [x for x in d['vers'] if x is not d]
            vdata = {re.sub(r'<[^>]+>', '', lab(x)): diff_text(x['body']) for x in others}
            sel = ('' if len(others) == 1 else '<select id="diffWith">' + ''.join(f'<option>{esc(k)}</option>' for k in vdata) + '</select>')
            h.append(f'<div class="diffbar"><label><input type="checkbox" id="showDiff"> Show differences from '
                     + (f'the {esc(next(iter(vdata)))} version' if len(others) == 1 else 'the version') + f'</label>{sel}'
                     '<span class="difflegend hidden"><mark class="d-chg">word</mark> differs or is absent in the other version &middot; '
                     '<span class="d-ins-key">+</span> text found only in the other version</span></div>'
                     '<script type="application/json" id="vdata">' + json.dumps(vdata, ensure_ascii=False).replace('</', '<\\/') + '</script>')
        if d.get('sn'):
            parts = series[(d['source'], d['series'])]
            h.append(f'<nav class="series"><strong>{esc(d["series"])}</strong> was printed in {d["sn"]} parts across issues. '
                     + ' '.join(f'<a class="btn{" on" if x is d else ""}" href="{x["id"]}.html" title="{esc(x["title"])} ({esc(x["issue"])})">{x["sk"]}</a>' for x in parts)
                     + f' <a class="btn" href="../series/{d["sslug"]}.html">Read all parts together</a></nav>')
        h.append(f'<article class="doc" id="doc">{render_body(d)}</article>')
        if d['notes']:
            h.append(f'<details class="note"><summary>Transcription note</summary><p>{esc(d["notes"])}</p></details>')
        om = OPUS.get(d['file'])
        model = {'opus': 'Claude Opus 5.5', 'opus+sonnet': 'Claude Opus 5.5 and Claude Sonnet 5.5'}.get(om, 'Claude Sonnet 5.5')
        if d['ia'] in HAIKU_BOOKS:
            model = 'Claude Haiku 5.5'
        other = sorted(set(re.findall(r'\*\[Page (\d+) was transcribed with ([^,\]]+), not Claude\.\]\*', d['body'])), key=lambda x: int(x[0]))
        missing = re.findall(r'\*\[Page (\d+) was not transcribed', d['body'])
        extra = ''
        if other:
            extra += f" The {'pages' if len(other) > 1 else 'page'} marked in the text (p.&nbsp;{', '.join(n for n, _ in other)}) {'were' if len(other) > 1 else 'was'} transcribed with {esc(other[0][1])} instead."
        if missing:
            extra += f" Not transcribed at all: p.&nbsp;{', '.join(missing)}."
        h.append(f'<aside class="disclaimer"><strong>Check the original.</strong> This text was transcribed from the page scans by an AI model '
                 f'({model}) reading the page images, and has not been proofread by a person.{extra} It may contain misreadings, dropped words or '
                 f'other errors. Before quoting or citing it, compare it with the <a href="{scan}" target="_blank">original scan on the Internet Archive</a>; '
                 f'the page numbers in the margin link to each page.</aside>')
        pv = docs[k - 1] if k else None
        nx = docs[k + 1] if k + 1 < len(docs) else None
        h.append('<div class="pn">' + (f'<a href="{pv["id"]}.html"><small>&larr; Previous</small>{esc(pv["title"])}</a>' if pv else '<a></a>')
                 + (f'<a href="{nx["id"]}.html"><small>Next &rarr;</small>{esc(nx["title"])}</a>' if nx else '<a></a>') + '</div>')
        js = r"""<script>(function(){function cp(b,t){navigator.clipboard&&navigator.clipboard.writeText(t).then(function(){var o=b.textContent;b.textContent='Copied';setTimeout(function(){b.textContent=o},1200)})}
var c=document.getElementById('citeBtn');c.onclick=function(){cp(c,c.dataset.cite)};var t=document.getElementById('textBtn');t.onclick=function(){cp(t,document.getElementById('doc').innerText)};
var q=new URLSearchParams(location.search).get('q');if(q){var words=q.replace(/"/g,'').split(/\s+/).filter(function(w){return w.length>1}).map(function(w){return w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')});
if(words.length){var re=new RegExp('('+(q.indexOf('"')>=0?q.replace(/"/g,'').trim().replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s+'):words.join('|'))+')','gi');
var w=document.createTreeWalker(document.getElementById('doc'),NodeFilter.SHOW_TEXT),ns=[],n;while(n=w.nextNode())ns.push(n);var first;
ns.forEach(function(n){if(!re.test(n.nodeValue))return;re.lastIndex=0;var s=document.createElement('span');s.innerHTML=n.nodeValue.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(re,'<mark>$1</mark>');n.parentNode.replaceChild(s,n);if(!first)first=s});
if(first)first.querySelector('mark').scrollIntoView({block:'center'})}}
var box=document.getElementById('showDiff');if(box){var art=document.getElementById('doc'),orig=art.innerHTML,V=JSON.parse(document.getElementById('vdata').textContent),
ws=document.getElementById('diffWith'),leg=document.querySelector('.difflegend');
function norm(w){w=w.replace(/[\u2018\u2019\u02bc`]/g,"'").replace(/[\u201c\u201d]/g,'"').replace(/^[^\w\u00c0-\u024f]+|[^\w\u00c0-\u024f]+$/g,'');
return w.length>1&&w===w.toUpperCase()&&/[A-Z]/.test(w)?w.charAt(0)+w.slice(1).toLowerCase():w}
function lcs(a,b){var n=a.length,m=b.length,w=m+1,L=new Uint16Array((n+1)*(m+1));for(var i=n-1;i>=0;i--)for(var j=m-1;j>=0;j--)L[i*w+j]=a[i]===b[j]?L[(i+1)*w+j+1]+1:Math.max(L[(i+1)*w+j],L[i*w+j+1]);
var pairs=[],i=0,j=0;while(i<n&&j<m){if(a[i]===b[j]){pairs.push([i,j]);i++;j++}else if(L[(i+1)*w+j]>=L[i*w+j+1])i++;else j++}return pairs}
function esc(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function show(){art.innerHTML=orig;leg.classList.toggle('hidden',!box.checked);if(!box.checked)return;
var other=V[ws?ws.value:Object.keys(V)[0]],ot=other.split(/\s+/).filter(function(x){return norm(x)}),on=ot.map(norm);
var walker=document.createTreeWalker(art,NodeFilter.SHOW_TEXT,{acceptNode:function(n){var p=n.parentNode.closest('p');if(p&&p.children.length==1&&p.firstElementChild.tagName=='STRONG'&&p.textContent.trim()==p.firstElementChild.textContent.trim())return NodeFilter.FILTER_REJECT;
return n.parentNode.closest('.pg,.pgbreak,.fn,sup,.ednote,.h,.fnote')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}}),nodes=[],n;
while(n=walker.nextNode())nodes.push(n);var toks=[];nodes.forEach(function(nd,k){var re=/\S+/g,m;while(m=re.exec(nd.nodeValue)){if(norm(m[0]))toks.push({n:k,s:m.index,e:m.index+m[0].length,w:norm(m[0])})}});
if(toks.length*on.length>60000000){leg.textContent='These versions are too long to compare in the browser.';return}
var pairs=lcs(toks.map(function(t){return t.w}),on),same=new Uint8Array(toks.length),ins={};pairs.forEach(function(p){same[p[0]]=1});
var pi=-1,pj=-1;pairs.concat([[toks.length,on.length]]).forEach(function(p){if(p[1]>pj+1){ins[pi]=ot.slice(pj+1,p[1]).join(' ')}pi=p[0];pj=p[1]});
var byNode={};toks.forEach(function(t,k){(byNode[t.n]=byNode[t.n]||[]).push([t,k])});
function insHtml(txt){var c=txt.split(' ').length;return c<=12?'<span class="d-ins" title="Only in the other version">+&#8201;'+esc(txt)+'</span>':
'<details class="d-ins-long"><summary>+ '+c+' words only in the other version</summary>'+esc(txt)+'</details>'}
nodes.forEach(function(nd,k){var list=byNode[k]||[],v=nd.nodeValue,out='',pos=0;list.forEach(function(x){var t=x[0],i=x[1];out+=esc(v.slice(pos,t.s));
var word=esc(v.slice(t.s,t.e));out+=same[i]?word:'<mark class="d-chg">'+word+'</mark>';if(ins[i]!==undefined)out+=' '+insHtml(ins[i]);pos=t.e});
if(k===0&&ins[-1]!==undefined)out=insHtml(ins[-1])+' '+out;out+=esc(v.slice(pos));var sp=document.createElement('span');sp.innerHTML=out;nd.parentNode.replaceChild(sp,nd)})}
box.onchange=show;if(ws)ws.onchange=show}
})();</script>"""
        open(f'{SITE}/doc/{d["id"]}.html', 'w').write(page(f"{d['title']} — {d['issue'] if d['source'] == 'yb' else SOURCES[d['source']] + ', ' + d['issue']}", sub, '', '\n'.join(h), depth=1, scripts=js))

    # ---- serialised texts, all parts on one page
    for (src, name), parts in series.items():
        h = [f'<div class="doc-head"><span class="tag {parts[0]["type"]}">{TYPES[parts[0]["type"]]}</span><h2>{esc(name)}</h2>'
             f'<dl class="meta"><dt>Printed in</dt><dd><em>{SOURCES[src]}</em>, in {len(parts)} parts: '
             + '; '.join(f'<a href="../doc/{x["id"]}.html">{esc(x["issue"])}</a>' for x in parts) + '</dd></dl></div>']
        for x in parts:
            h.append(f'<h3 class="parthead" id="part-{x["sk"]}">Part {x["sk"]}: <a href="../doc/{x["id"]}.html">{esc(x["title"])}</a>'
                     f'<small>{SOURCES[src]}, {esc(x["issue"])}{", pp. " + esc(x["pages"]) if x["pages"] else ""}</small></h3>')
            h.append(f'<article class="doc">{render_body(x)}</article>')
            if x['notes']:
                h.append(f'<details class="note"><summary>Transcription note (part {x["sk"]})</summary><p>{esc(x["notes"])}</p></details>')
        h.append('<aside class="disclaimer"><strong>Check the original.</strong> These texts were transcribed from the page scans by an AI model reading the '
                 'page images and have not been proofread by a person; the model used is named at the foot of each part\'s own page. '
                 'Before quoting or citing, compare with the original scans: the page numbers in the margin link to each page.</aside>')
        open(f'{SITE}/series/{parts[0]["sslug"]}.html', 'w').write(page(f'{name} \u2014 {SOURCES[src]}', sub, '', '\n'.join(h), depth=1))

    # ---- search
    data = [{'i': d['id'], 't': d['title'], 'y': d['type'], 's': d['source'], 'n': d['issue'], 'd': fmt_date(d['date']), 'o': d['sortdate'],
             'w': who(d), 'p': d['pages'], 'x': plain(d['body'])} for d in listed]
    data += [{'i': '', 'u': x['url'], 't': x['title'], 'y': 'external', 's': 'wj', 'n': 'English documents', 'd': fmt_date(x['date']), 'o': x['sortdate'],
              'w': x['title_ja'], 'p': '', 'x': ''} for x in externals]
    open(f'{SITE}/data.js', 'w').write('window.DOCS=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';')
    s = ['<div class="controls"><input type="search" id="q" placeholder="Search the full text of all documents&hellip;" autofocus>'
         '<div class="chips" id="typeChips">' + ''.join(f'<span class="chip on" data-v="{t}">{TYPES_PL[t]}</span>' for t in TYPES if counts[t]) + '<span class="chip" data-all="1" title="Show every category">Show all</span><span class="chiphint">Click a category to hide or show it. Option-click (Alt-click on Windows) to show only that one.</span></div>'
         '<div class="chips" id="srcChips">' + ''.join(f'<span class="chip on" data-v="{x}">{n}</span>' for x, n in SOURCES.items()) + '</div>'
         '<select id="scope"><option value="all">Full text</option><option value="title">Titles only</option></select>'
         '<span class="count" id="count"></span></div>'
         '<p class="hint" id="hint">All words must appear. Put a phrase in &ldquo;double quotes&rdquo; to match it exactly. Results are ordered by date.</p><div id="results"></div>']
    js = r"""<script src="data.js"></script><script>(function(){
var T={treaty:'Treaty',law:'Law',speech:'Speech',document:'Document',summary:'Summary',list:'List',programme:'Programme',report:'Report',review:'Review',statistics:'Statistics',profile:'Profile',external:'WJ ↗'},S={tg:'Tokyo Gazette',cj:'Contemporary Japan',yb:'Year Books',wj:'The World and Japan'};
var on={type:{},src:{}};function chips(id,k){var c=document.getElementById(id);[].forEach.call(c.children,function(x){if(x.dataset.v)on[k][x.dataset.v]=true;x.onclick=function(ev){var kids=[].filter.call(c.children,function(y){return y.dataset.v});
if(x.dataset.all){kids.forEach(function(y){y.classList.add('on');on[k][y.dataset.v]=true})}
else if(ev.altKey){kids.forEach(function(y){y.classList.toggle('on',y==x);on[k][y.dataset.v]=y==x})}
else{x.classList.toggle('on');on[k][x.dataset.v]=x.classList.contains('on');
if(!kids.some(function(y){return y.classList.contains('on')})){kids.forEach(function(y){y.classList.add('on');on[k][y.dataset.v]=true})}}run()}})}
function e(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')}function rx(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
var D=window.DOCS;D.forEach(function(d){d.lx=d.x.toLowerCase();d.lt=(d.t+' '+d.w).toLowerCase()});D.sort(function(a,b){return a.o<b.o?-1:a.o>b.o?1:0});
var q=document.getElementById('q'),R=document.getElementById('results'),C=document.getElementById('count'),sc=document.getElementById('scope'),tm;
function terms(v){var t=[],m,re=/"([^"]+)"|(\S+)/g;while(m=re.exec(v)){var w=(m[1]||m[2]).toLowerCase().trim();if(w)t.push(w)}return t}
function run(){var v=q.value.trim(),t=terms(v),title=sc.value=='title';history.replaceState(null,'',v?'?q='+encodeURIComponent(v):location.pathname);
document.getElementById('hint').classList.toggle('hidden',!!v);if(!t.length){R.innerHTML='';C.textContent=D.length+' entries';return}
var hl=new RegExp('('+t.map(rx).join('|')+')','gi'),out=[],n=0;
D.forEach(function(d){if(!on.type[d.y]||!on.src[d.s])return;var hay=title?d.lt:d.lt+' '+d.lx;for(var i=0;i<t.length;i++)if(hay.indexOf(t[i])<0)return;n++;if(n>300)return;
var sn='',p=-1;for(var i=0;i<t.length&&p<0;i++)p=d.lx.indexOf(t[i]);if(p>=0&&!title){var a=Math.max(0,p-110),b=Math.min(d.x.length,p+190);sn=(a?'… ':'')+e(d.x.slice(a,b)).replace(hl,'<mark>$1</mark>')+(b<d.x.length?' …':'');
var cnt=0;t.forEach(function(w){var k=-1;while((k=d.lx.indexOf(w,k+1))>=0)cnt++});sn+=' <span class="pg">('+cnt+' match'+(cnt>1?'es':'')+')</span>'}
out.push('<div class="result"><h3><span class="tag '+d.y+'">'+T[d.y]+'</span> '+(d.u?'<a href="'+e(d.u)+'" target="_blank" rel="noopener">':'<a href="doc/'+d.i+'.html?q='+encodeURIComponent(v)+'">')+e(d.t).replace(hl,'<mark>$1</mark>')+'</a></h3><div class="rmeta">'+(d.w?e(d.w)+' · ':'')+(d.d?e(d.d)+' · ':'')+(d.s=='yb'?'<em>'+e(d.n)+'</em>':d.s=='wj'?'external link: <em>The World and Japan</em>':'<em>'+S[d.s]+'</em>, '+e(d.n))+(d.p?', p. '+e(d.p):'')+'</div>'+(sn?'<div class="snip">'+sn+'</div>':'')+'</div>')});
R.innerHTML=out.join('')||'<p class="hint">No texts match.</p>';C.textContent=n+' entr'+(n==1?'y':'ies')+(n>300?' (first 300 shown)':'')}
chips('typeChips','type');chips('srcChips','src');q.oninput=function(){clearTimeout(tm);tm=setTimeout(run,140)};sc.onchange=run;
var ps=document.createElement('script');ps.src='wj_postwar.js';ps.onload=function(){(window.WJPOST||[]).forEach(function(e){D.push({i:'',u:e.u,t:e.t,y:'external',s:'wj',n:'',d:e.d,o:e.o,w:e.j,p:'',x:'',lx:'',lt:(e.t+' '+e.j).toLowerCase()})});
D.sort(function(a,b){return a.o<b.o?-1:a.o>b.o?1:0});if(q.value.trim())run();else C.textContent=D.length+' entries'};document.body.appendChild(ps);
var p=new URLSearchParams(location.search).get('q');if(p)q.value=p;run()})();</script>"""
    open(f'{SITE}/search.html', 'w').write(page('Search — Treaties, Laws and Speeches', sub, 'search', '\n'.join(s), scripts=js))
    print(f'{len(docs)} texts ->', SITE, counts)
    words = sum(len(d['body'].split()) for d in docs)
    print('words', words)
    for p in problems:
        print('PROBLEM', p)


if __name__ == '__main__':
    build()
