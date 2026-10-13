import re,html,json
def clean(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip()
# ---- Tokyo Gazette
s=open('tg.html',encoding='utf-8').read()
tg=[];cur=None;vol=None;depth=0
for m in re.finditer(r'<h2 class="volume-heading"[^>]*>(.*?)</h2>|<span class="issue-date">(.*?)</span> <span class="issue-num">(.*?)</span>|<div class="issue-link"><a href="https://archive.org/details/([^"]+)"|<ul class="(entry-list|sub-entries|sub-sub-entries)">|<li class="entry-item">(.*?)</li>',s,re.S):
    if m.group(1): vol=clean(m.group(1))
    elif m.group(2): cur={'vol':vol,'date':clean(m.group(2)),'num':clean(m.group(3)),'ia':None,'entries':[]}; tg.append(cur)
    elif m.group(4): cur['ia']=m.group(4)
    elif m.group(5): depth={'entry-list':0,'sub-entries':1,'sub-sub-entries':2}[m.group(5)]
    elif m.group(6):
        li=m.group(6)
        a=re.search(r'<span class="entry-attrib">(.*?)</span>',li,re.S)
        attrib=clean(a.group(1)) if a else ''
        t=re.search(r'<span class="entry-text">(.*?)(<span class="entry-attrib">|</span> <span class="entry-page">|</span>\s*$)',li,re.S)
        title=clean(t.group(1)) if t else clean(li)
        p=re.search(r'/page/n(\d+)/mode/1up"[^>]*>(.*?)</a>',li)
        cur['entries'].append({'d':depth,'title':title,'attrib':attrib,'n':int(p.group(1)) if p else None,'p':clean(p.group(2)).replace('p. ','').replace('p.\xa0','') if p else ''})
json.dump(tg,open('tg.json','w'),ensure_ascii=False,indent=1)
print('TG issues',len(tg),'entries',sum(len(i['entries']) for i in tg), 'no ia',[i['date'] for i in tg if not i['ia']])
# ---- Contemporary Japan
s=open('cj.html',encoding='utf-8').read()
s=s[s.find('<h3><strong>1941 Volume X'):]
s=s[:s.find('</div><!-- .entry-content')] if '</div><!-- .entry-content' in s else s
cj=[];cur=None;depth=0
for m in re.finditer(r'<p><a id="(\d+)"></a>(.*?)</p>|<ul>|</ul>|<li>(.*?)(?=<ul>|</li>|<li>)',s,re.S):
    g=m.group(0)
    if m.group(1):
        ia=re.search(r'archive\.org/details/([^/"]+)',m.group(2))
        cur={'anchor':m.group(1),'date':clean(m.group(2)).replace(' – ToC','').strip(' –'),'ia':ia.group(1) if ia else None,'entries':[]}; cj.append(cur); depth=0
    elif g=='<ul>': depth+=1
    elif g=='</ul>': depth-=1
    elif m.group(3) is not None and cur:
        li=m.group(3); p=re.search(r'archive\.org/details/([^/"]+)/page/n(\d+)',li)
        if p and not cur['ia']: cur['ia']=p.group(1)
        cur['entries'].append({'d':depth-1,'title':clean(li),'n':int(p.group(2)) if p else None})
json.dump(cj,open('cj.json','w'),ensure_ascii=False,indent=1)
print('CJ issues',len(cj),'entries',sum(len(i['entries']) for i in cj))
for i in cj: print(i['anchor'],i['date'],i['ia'],len(i['entries']),sum(1 for e in i['entries'] if e['d']>0))
