"""Build the static site in docs/ (served by GitHub Pages) from the transcribed texts in texts/<tg|cj>/<ia>/*.md.

usage: python3 scripts/build.py
Output: docs/index.html (browse), docs/search.html (full-text search), docs/doc/<id>.html (one per text),
docs/data.js (search index). Everything is self-contained and opens from file://.
"""
import html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = f'{ROOT}/docs'
SOURCES = {'tg': 'Tokyo Gazette', 'cj': 'Contemporary Japan'}
TYPES = {'treaty': 'Treaty', 'law': 'Law', 'speech': 'Speech', 'document': 'Document', 'list': 'List'}
TYPES_PL = {'treaty': 'Treaties', 'law': 'Laws', 'speech': 'Speeches', 'document': 'Other documents', 'list': 'Lists of laws promulgated'}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
esc = html.escape


# ---------- loading ----------

def issue_order():
    """(source, ia, issue label) -> sort position, from the parsed index pages."""
    order = {}
    for src in SOURCES:
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
                for k in ('title', 'issue', 'leaf', 'pages', 'date', 'author', 'parties', 'section', 'notes'):
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
                meta['sortdate'] = meta['date'] or issue_sortdate(meta['issue'])
                docs.append(meta)
    docs.sort(key=lambda d: (list(SOURCES).index(d['source']), d['ipos'], d['file']))
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
    return f'https://archive.org/details/{ia}/page/n{leaf}/mode/1up'


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
            for r in rows[2:]:
                h += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
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


def plain(body):
    t = re.sub(r'\[\[p\.[^\]]*\]\]', ' ', body)
    t = re.sub(r'[#*_|>]|\[\^\w+\]:?', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------- pages ----------

CSS = r""":root{--bg:#fff;--fg:#1a1a1a;--fg-muted:#5f5f5f;--fg-faint:#8a8a8a;--accent:#003a87;--on-accent:#fff;
--header-bg:#f5f5f5;--card-bg:#fff;--card-border:#dcdcdc;--input-border:#bbb;--input-bg:#fff;--dotted:#ddd;--rule:#e6e6e6;
--tag-bg:#f0f0f0;--mark:#fff2a8;--treaty:#8a3b12;--law:#1d5c3a;--speech:#003a87;--document:#5b4a7a;--list:#5f5f5f;
--ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;--serif:Georgia,"Times New Roman",serif;--r:3px}
[data-theme="dark"]{--bg:#1a1a1a;--fg:#ddd;--fg-muted:#aaa;--fg-faint:#808080;--accent:#6da3e0;--on-accent:#111;
--header-bg:#242424;--card-bg:#242424;--card-border:#444;--input-border:#555;--input-bg:#2a2a2a;--dotted:#444;--rule:#333;
--tag-bg:#333;--mark:#6b5a00;--treaty:#e0a27d;--law:#7fc79f;--speech:#6da3e0;--document:#b3a2d6;--list:#aaa}
*{margin:0;padding:0;box-sizing:border-box}
html{font-size:100%;-webkit-text-size-adjust:100%}
body{font-family:var(--serif);font-size:1rem;color:var(--fg);background:var(--bg);line-height:1.5}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:56.25rem;margin:0 auto;padding:0 1.25rem}
header{background:var(--header-bg);border-bottom:3px solid var(--accent);padding:1.75rem 0 1.1rem;text-align:center}
header h1{font-size:1.6rem;margin-bottom:.25rem;letter-spacing:.03em}header h1 a{color:var(--fg)}header h1 a:hover{text-decoration:none}
header .subtitle{font-size:.95rem;color:var(--fg-muted);font-style:italic;margin-bottom:.9rem}
nav{display:flex;justify-content:center;gap:.6rem;flex-wrap:wrap}
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
.chip.on[data-v=treaty]{background:var(--treaty);border-color:var(--treaty)}.chip.on[data-v=law]{background:var(--law);border-color:var(--law)}
.chip.on[data-v=speech]{background:var(--speech);border-color:var(--speech)}.chip.on[data-v=document]{background:var(--document);border-color:var(--document)}
.chip.on[data-v=list]{background:var(--list);border-color:var(--list)}
.controls select,.controls input[type=search]{font-weight:400;color:var(--fg);border-color:var(--input-border);justify-content:flex-start;cursor:auto;max-width:100%}
.controls select{cursor:pointer}
.controls input[type=search]{flex:1 1 14rem;min-width:10rem;font-size:.9375rem}
.controls select:focus,.controls input:focus,.chip:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.controls{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--rule);padding:.6rem 0;margin-top:.75rem;
display:flex;gap:.5rem .9rem;flex-wrap:wrap;align-items:center}
.chips{display:flex;gap:.3rem;flex-wrap:wrap}
.count{font-family:var(--ui);font-size:.8125rem;color:var(--fg-faint);margin-left:auto;white-space:nowrap}
footer{text-align:center;padding:1.5rem 0;margin-top:2.5rem;border-top:1px solid var(--dotted);font-family:var(--ui);font-size:.8125rem;color:var(--fg-faint)}
header{position:relative}
.display-toolbar{position:absolute;top:.6rem;right:.75rem;display:flex;gap:.2rem}
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
.tag{display:inline-block;box-sizing:border-box;width:5.25rem;padding:.12rem 0;text-align:center;font-family:var(--ui);font-size:.625rem;font-weight:700;line-height:1.3;
letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;overflow:hidden;border-radius:var(--r);border:1.5px solid currentColor;vertical-align:middle}
.tag.treaty{color:var(--treaty)}.tag.law{color:var(--law)}.tag.speech{color:var(--speech)}.tag.document{color:var(--document)}.tag.list{color:var(--list)}
.hidden{display:none!important}
/* document page */
.doc-head{margin:1.6rem 0 1.1rem;padding-bottom:.9rem;border-bottom:1px solid var(--rule)}
.doc-head h2{font-size:1.5rem;line-height:1.25;margin:.5rem 0 .6rem;overflow-wrap:anywhere}
.meta{font-family:var(--ui);font-size:.84rem;display:grid;grid-template-columns:max-content minmax(0,1fr);gap:.2rem .9rem}
.meta dt{color:var(--fg-faint)}.meta dd{color:var(--fg);overflow-wrap:anywhere}
.note{margin-top:.7rem;font-family:var(--ui);font-size:.84rem;color:var(--fg-muted);background:var(--tag-bg);padding:.5rem .75rem;border-radius:var(--r)}
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
.illeg{color:#b00020;font-style:italic}.fnote{font-size:.85em;color:var(--fg-muted)}sup.fn{font-size:.7em}
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
.display-toolbar{position:static;justify-content:center;margin-top:.7rem}.back-to-top{bottom:.9rem;right:.9rem}}
@media print{header nav,.display-toolbar,.back-to-top,.pn,.tools,.controls{display:none}.doc{font-size:12pt}}
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
<p>Only texts printed in full in the journals are included; commentary, summaries and articles about them are not.
The issues covered are those indexed on the <a href="https://froginawell.net/tokyo-gazette/">Tokyo Gazette table of contents</a> and
<a href="https://froginawell.net/frog/sources/primary-source-nuggets/contemporary-japan/">Contemporary Japan</a> pages at Frog in a Well,
and scanned on the Internet Archive.</p>
<p>These are official translations and statements of the wartime Japanese state and its allies, and should be read as such.</p>
<p><strong>Transcription.</strong> The texts were transcribed from the page scans by a large language model reading the page images,
and have not been proofread by a person. Original spelling and romanisation are kept. Page numbers in the margin link to the page
of the scan on the Internet Archive: check the scan before quoting.</p>"""


def page(title, subtitle, active, body, depth=0, extra_head='', scripts=''):
    up = '../' * depth
    nav = ''.join(f'<a href="{up}{h}"{" class=active" if a == active else ""}>{t}</a>' for a, h, t in
                  [('browse', 'index.html', 'Browse'), ('search', 'search.html', 'Search')])
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}style.css"><script src="{up}common.js"></script>{extra_head}
</head><body>
<header><div class="container"><h1><a href="{up}index.html">Treaties, Laws and Speeches</a></h1>
<div class="subtitle">{subtitle}</div>
<nav>{nav}<a href="#" id="navAbout">About</a></nav></div>
<div class="display-toolbar"><button id="fontDown" title="Smaller text" aria-label="Smaller text">A&minus;</button><button id="fontUp" title="Larger text" aria-label="Larger text">A+</button><button id="themeBtn" title="Light / dark" aria-label="Light or dark theme">&#9680;</button></div></header>
<div class="container">
{body}
</div>
<footer><div class="container">Texts from the <em>Tokyo Gazette</em> and <em>Contemporary Japan</em>, 1937&ndash;1945 &middot;
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
    w = who(d)
    att = f' <span class="entry-attrib">({esc(w)})</span>' if w and w.lower() not in d['title'].lower() else ''
    return (f'<li class="entry-item" data-type="{d["type"]}" data-src="{d["source"]}" data-date="{d["sortdate"]}">'
            f'<span class="tag {d["type"]}">{TYPES[d["type"]]}</span>'
            f'<span class="entry-text"><a href="{up}doc/{d["id"]}.html">{esc(d["title"])}</a>{att}</span>'
            f'<span class="entry-page">{esc(fmt_date(d["date"]))}</span></li>')


def build():
    docs, problems = load()
    ids = {}
    for d in docs:
        if d['id'] in ids:
            n = 2
            while f"{d['id']}-{n}" in ids:
                n += 1
            d['id'] = f"{d['id']}-{n}"
        ids[d['id']] = d
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(f'{SITE}/doc')
    open(f'{SITE}/.nojekyll', 'w').write('')
    open(f'{SITE}/style.css', 'w').write(CSS)
    open(f'{SITE}/common.js', 'w').write(COMMON_JS)
    counts = {t: sum(1 for d in docs if d['type'] == t) for t in TYPES}
    sub = f'Verbatim texts from the <em>Tokyo Gazette</em> and <em>Contemporary Japan</em>, 1937&ndash;1945'

    # ---- browse
    b = [f'<p class="intro">{len(docs)} texts printed in full in two English-language periodicals of wartime Japan: '
         + ', '.join(f'{counts[t]} {TYPES_PL[t].lower()}' for t in TYPES) + '. Each links to the page of the original scan.</p>']
    b.append('<div class="controls"><div class="chips" id="typeChips">'
             + ''.join(f'<span class="chip on" data-v="{t}">{TYPES_PL[t]}</span>' for t in TYPES) + '</div>'
             '<div class="chips" id="srcChips">' + ''.join(f'<span class="chip on" data-v="{s}">{n}</span>' for s, n in SOURCES.items()) + '</div>'
             '<div class="chips" id="viewChips"><span class="chip on" data-v="issue">By issue</span><span class="chip" data-v="date">By date</span></div>'
             '<select id="jumpSelect"><option value="">&mdash; Jump to an issue &mdash;</option></select>'
             '<span class="count" id="count"></span></div>')
    b.append('<div id="byIssue">')
    cur_src = cur_issue = None
    for d in docs:
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
                     f'<h3 class="issue-heading">{esc(d["issue"])}<a class="issue-num" href="https://archive.org/details/{d["ia"]}" target="_blank">scan &rarr;</a></h3><ul class="entry-list">')
        b.append(entry(d))
    if docs:
        b.append('</ul></section></section>')
    b.append('</div><div id="byDate" class="hidden">')
    year = None
    for d in sorted(docs, key=lambda d: (d['sortdate'], d['file'])):
        y = d['sortdate'][:4]
        if y != year:
            if year:
                b.append('</ul></section>')
            year = y
            b.append(f'<section class="iss"><h2 class="volume-heading">{y}</h2><ul class="entry-list">')
        b.append(entry(d))
    if docs:
        b.append('</ul></section>')
    b.append('</div>')
    js = r"""<script>(function(){
var on={type:{},src:{}};function chips(id,k,multi){var c=document.getElementById(id);[].forEach.call(c.children,function(x){if(multi)on[k][x.dataset.v]=true;
x.onclick=function(){if(multi){var all=[].every.call(c.children,function(y){return y.classList.contains('on')});
if(all){[].forEach.call(c.children,function(y){y.classList.remove('on');on[k][y.dataset.v]=false})}
x.classList.toggle('on');on[k][x.dataset.v]=x.classList.contains('on');
if(![].some.call(c.children,function(y){return y.classList.contains('on')})){[].forEach.call(c.children,function(y){y.classList.add('on');on[k][y.dataset.v]=true})}}
else{[].forEach.call(c.children,function(y){y.classList.toggle('on',y==x)});
document.getElementById('byIssue').classList.toggle('hidden',x.dataset.v!='issue');document.getElementById('byDate').classList.toggle('hidden',x.dataset.v!='date');
document.getElementById('jumpSelect').classList.toggle('hidden',x.dataset.v!='issue')}
apply()}})}
function apply(){var n=0,vis=document.getElementById('byIssue').classList.contains('hidden')?'byDate':'byIssue';
[].forEach.call(document.querySelectorAll('.entry-item'),function(li){var s=on.type[li.dataset.type]&&on.src[li.dataset.src];li.classList.toggle('hidden',!s);if(s&&li.closest('#'+vis))n++});
[].forEach.call(document.querySelectorAll('.iss,.src'),function(s){s.classList.toggle('hidden',!s.querySelector('.entry-item:not(.hidden)'))});
document.getElementById('count').textContent=n+' texts'}
chips('typeChips','type',true);chips('srcChips','src',true);chips('viewChips','view',false);
var sel=document.getElementById('jumpSelect');[].forEach.call(document.querySelectorAll('#byIssue .iss'),function(s){var o=document.createElement('option');o.value=s.id;o.innerHTML=s.dataset.label;sel.appendChild(o)});
sel.onchange=function(){if(this.value)document.getElementById(this.value).scrollIntoView({behavior:'smooth',block:'start'})};apply()})();</script>"""
    open(f'{SITE}/index.html', 'w').write(page('Treaties, Laws and Speeches — Tokyo Gazette & Contemporary Japan', sub, 'browse', '\n'.join(b), scripts=js))

    # ---- documents
    for k, d in enumerate(docs):
        rows = [('Type', TYPES[d['type']]), ('Date', fmt_date(d['date'])),
                ('Speaker / issued by' if d['type'] in ('speech', 'document') else 'Author', d['author']),
                ('Parties', d['parties'].replace(';', ' · ')), ('Printed in', f"<em>{SOURCES[d['source']]}</em>, {esc(d['issue'])}"
                 + (f", pp.&nbsp;{esc(d['pages'])}" if re.search(r'\D', d['pages']) else (f", p.&nbsp;{esc(d['pages'])}" if d['pages'] else ''))),
                ('Section', d['section'])]
        scan = ia_page(d['ia'], d['leaf']) if d['leaf'] is not None else f"https://archive.org/details/{d['ia']}"
        meta = ''.join(f'<dt>{a}</dt><dd>{v if a == "Printed in" else esc(v)}</dd>' for a, v in rows if v)
        cite = f"“{d['title']},” {SOURCES[d['source']]} ({d['issue']}){': ' + d['pages'] if d['pages'] else ''}."
        h = [f'<div class="doc-head"><span class="tag {d["type"]}">{TYPES[d["type"]]}</span><h2>{esc(d["title"])}</h2><dl class="meta">{meta}</dl>']
        if d['notes']:
            h.append(f'<div class="note"><strong>Transcription note:</strong> {esc(d["notes"])}</div>')
        h.append(f'<div class="tools"><a href="{scan}" target="_blank">View the scan on the Internet Archive &rarr;</a>'
                 f'<button id="citeBtn" data-cite="{esc(cite)}">Copy citation</button><button id="textBtn">Copy text</button></div></div>')
        h.append(f'<article class="doc" id="doc">{render_body(d)}</article>')
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
if(first)first.querySelector('mark').scrollIntoView({block:'center'})}}})();</script>"""
        open(f'{SITE}/doc/{d["id"]}.html', 'w').write(page(f"{d['title']} — {SOURCES[d['source']]}, {d['issue']}", sub, '', '\n'.join(h), depth=1, scripts=js))

    # ---- search
    data = [{'i': d['id'], 't': d['title'], 'y': d['type'], 's': d['source'], 'n': d['issue'], 'd': fmt_date(d['date']), 'o': d['sortdate'],
             'w': who(d), 'p': d['pages'], 'x': plain(d['body'])} for d in docs]
    open(f'{SITE}/data.js', 'w').write('window.DOCS=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';')
    s = ['<div class="controls"><input type="search" id="q" placeholder="Search the full text of all documents&hellip;" autofocus>'
         '<div class="chips" id="typeChips">' + ''.join(f'<span class="chip on" data-v="{t}">{TYPES_PL[t]}</span>' for t in TYPES) + '</div>'
         '<div class="chips" id="srcChips">' + ''.join(f'<span class="chip on" data-v="{x}">{n}</span>' for x, n in SOURCES.items()) + '</div>'
         '<select id="scope"><option value="all">Full text</option><option value="title">Titles only</option></select>'
         '<span class="count" id="count"></span></div>'
         '<p class="hint" id="hint">All words must appear. Put a phrase in &ldquo;double quotes&rdquo; to match it exactly. Results are ordered by date.</p><div id="results"></div>']
    js = r"""<script src="data.js"></script><script>(function(){
var T={treaty:'Treaty',law:'Law',speech:'Speech',document:'Document',list:'List'},S={tg:'Tokyo Gazette',cj:'Contemporary Japan'};
var on={type:{},src:{}};function chips(id,k){var c=document.getElementById(id);[].forEach.call(c.children,function(x){on[k][x.dataset.v]=true;x.onclick=function(){
var all=[].every.call(c.children,function(y){return y.classList.contains('on')});if(all){[].forEach.call(c.children,function(y){y.classList.remove('on');on[k][y.dataset.v]=false})}
x.classList.toggle('on');on[k][x.dataset.v]=x.classList.contains('on');
if(![].some.call(c.children,function(y){return y.classList.contains('on')})){[].forEach.call(c.children,function(y){y.classList.add('on');on[k][y.dataset.v]=true})}run()}})}
function e(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')}function rx(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
var D=window.DOCS;D.forEach(function(d){d.lx=d.x.toLowerCase();d.lt=(d.t+' '+d.w).toLowerCase()});D.sort(function(a,b){return a.o<b.o?-1:a.o>b.o?1:0});
var q=document.getElementById('q'),R=document.getElementById('results'),C=document.getElementById('count'),sc=document.getElementById('scope'),tm;
function terms(v){var t=[],m,re=/"([^"]+)"|(\S+)/g;while(m=re.exec(v)){var w=(m[1]||m[2]).toLowerCase().trim();if(w)t.push(w)}return t}
function run(){var v=q.value.trim(),t=terms(v),title=sc.value=='title';history.replaceState(null,'',v?'?q='+encodeURIComponent(v):location.pathname);
document.getElementById('hint').classList.toggle('hidden',!!v);if(!t.length){R.innerHTML='';C.textContent=D.length+' texts';return}
var hl=new RegExp('('+t.map(rx).join('|')+')','gi'),out=[],n=0;
D.forEach(function(d){if(!on.type[d.y]||!on.src[d.s])return;var hay=title?d.lt:d.lt+' '+d.lx;for(var i=0;i<t.length;i++)if(hay.indexOf(t[i])<0)return;n++;if(n>300)return;
var sn='',p=-1;for(var i=0;i<t.length&&p<0;i++)p=d.lx.indexOf(t[i]);if(p>=0&&!title){var a=Math.max(0,p-110),b=Math.min(d.x.length,p+190);sn=(a?'… ':'')+e(d.x.slice(a,b)).replace(hl,'<mark>$1</mark>')+(b<d.x.length?' …':'');
var cnt=0;t.forEach(function(w){var k=-1;while((k=d.lx.indexOf(w,k+1))>=0)cnt++});sn+=' <span class="pg">('+cnt+' match'+(cnt>1?'es':'')+')</span>'}
out.push('<div class="result"><h3><span class="tag '+d.y+'">'+T[d.y]+'</span> <a href="doc/'+d.i+'.html?q='+encodeURIComponent(v)+'">'+e(d.t).replace(hl,'<mark>$1</mark>')+'</a></h3><div class="rmeta">'+(d.w?e(d.w)+' · ':'')+(d.d?e(d.d)+' · ':'')+'<em>'+S[d.s]+'</em>, '+e(d.n)+(d.p?', p. '+e(d.p):'')+'</div>'+(sn?'<div class="snip">'+sn+'</div>':'')+'</div>')});
R.innerHTML=out.join('')||'<p class="hint">No texts match.</p>';C.textContent=n+' text'+(n==1?'':'s')+(n>300?' (first 300 shown)':'')}
chips('typeChips','type');chips('srcChips','src');q.oninput=function(){clearTimeout(tm);tm=setTimeout(run,140)};sc.onchange=run;
var p=new URLSearchParams(location.search).get('q');if(p)q.value=p;run()})();</script>"""
    open(f'{SITE}/search.html', 'w').write(page('Search — Treaties, Laws and Speeches', sub, 'search', '\n'.join(s), scripts=js))
    print(f'{len(docs)} texts ->', SITE, counts)
    words = sum(len(d['body'].split()) for d in docs)
    print('words', words)
    for p in problems:
        print('PROBLEM', p)


if __name__ == '__main__':
    build()
