"""Rejoin words that were left split by an end-of-column or end-of-page hyphen ("associa-" / "tion").
The transcribers wrote one page or column per step, so a word broken across that boundary stayed in two pieces.
The whole word is put before the page marker. If the joined form is not a dictionary word the hyphen is kept
(e.g. "above-" / "mentioned" -> "above-mentioned"). usage: fix_linebreak_hyphens.py [--dry]"""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
words = set(w.strip().lower() for w in open('/usr/share/dict/words'))
corpus = set()
for f in glob.glob(f'{ROOT}/texts/*/*/*.md'):
    corpus.update(re.findall(r"[A-Za-z]{5,}", open(f, encoding='utf-8').read()))
def known(w):
    if w in corpus:      # the unbroken form is used elsewhere in the collection (names such as Manchoukuo)
        return True
    w = w.lower()
    return any(x in words for x in (w, w.rstrip('s'), re.sub(r'(ed|ing|es|ly|d)$', '', w), re.sub(r'ies$', 'y', w), re.sub(r'(ed|ing)$', 'e', w),
                                    w.replace('our', 'or'), w.replace('ise', 'ize'), w.replace('isation', 'ization')))
PAT = re.compile(r'([A-Za-z]+)-[ \t]*\n((?:[ \t]*\n)*(?:\[\[p\.[^\]]*\]\][ \t]*\n(?:[ \t]*\n)*)?)([a-z]+)([^\s]*)[ \t]?')
dry = '--dry' in sys.argv
n = kept = 0
for f in sorted(glob.glob(f'{ROOT}/texts/*/*/*.md')):
    s = open(f, encoding='utf-8').read()
    head, sep, body = s.partition('\n---\n')
    def rep(m):
        global n, kept
        a, gap, b, tail = m.groups()
        joined = a + b if known(a + b) else a + '-' + b
        n += 1; kept += '-' in joined
        if dry and "-" in joined: print('  ', os.path.basename(f)[:30], repr(a + '-|' + b), '->', joined)
        return joined + tail + '\n' + gap if gap.strip() else joined + tail + ' '
    new = PAT.sub(rep, body)
    if new != body and not dry:
        open(f, 'w', encoding='utf-8').write(head + sep + new)
print('joined', n, 'of which hyphen kept', kept)
