# -*- coding: utf-8 -*-
"""Rebuild the question->figure mapping from PDF coordinates (group-aware),
and diff it against the mapping currently in practice/."""
import fitz, json, os, csv, re, collections, hashlib, shutil

SRC = r"D:\ai-antigravity\ipas-aiap\official_sources"
DST = r"D:\ai-antigravity\ipas-aiap\verification"
PRAC = r"D:\ai-antigravity\ipas-aiap\practice"
FIGDIR = os.path.join(DST, 'figures')
HERE = os.path.dirname(os.path.abspath(__file__))
ZOOM, PAD = 3.0, 6

pdfdata = json.load(open(os.path.join(HERE, 'pdf_extracted.json'), encoding='utf-8'))
det = {r['編號']: r for r in csv.DictReader(open(os.path.join(DST, '02_逐題檢查明細.csv'), encoding='utf-8-sig'))}
prac = list(csv.DictReader(open(os.path.join(PRAC, 'FALO-IPAS-AIAP-20260802.csv'), encoding='utf-8-sig')))

shutil.rmtree(FIGDIR, ignore_errors=True)
os.makedirs(FIGDIR, exist_ok=True)

loc = {qid: (r['對應PDF'], int(r['PDF題號'])) for qid, r in det.items()}
rev = {v: k for k, v in loc.items()}

docs = {}
def doc(p):
    if p not in docs:
        docs[p] = fitz.open(os.path.join(SRC, p))
    return docs[p]

def crop(pdfname, ims, stem):
    """Render the union box of `ims`, one file per page. Returns filenames."""
    d = doc(pdfname)
    out = []
    bypage = collections.defaultdict(list)
    for im in ims:
        bypage[im['page']].append(im)
    for pg, g in sorted(bypage.items()):
        page = d[pg - 1]
        r = fitz.Rect(max(0, min(i['x0'] for i in g) - PAD),
                      max(0, min(i['y0'] for i in g) - PAD),
                      min(page.rect.x1, max(i['x1'] for i in g) + PAD),
                      min(page.rect.y1, max(i['y1'] for i in g) + PAD))
        fn = f'{stem}.png' if len(bypage) == 1 else f'{stem}_p{pg}.png'
        open(os.path.join(FIGDIR, fn), 'wb').write(
            page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=r).tobytes('png'))
        out.append(fn)
    return out

# ---- shared (group) figures: rendered once, referenced by every group member
group_files, group_of = {}, {}
for pdfname, v in pdfdata.items():
    for g in v.get('groups', []):
        first = rev.get((pdfname, g['first']))
        if not first:
            continue
        files = crop(pdfname, g['shared_images'], f'fig_G_{first}') if g['shared_images'] else []
        for n in range(g['first'], g['last'] + 1):
            qid = rev.get((pdfname, n))
            if qid:
                group_files[qid] = files
                group_of[qid] = (g['first'], g['last'])

out = []
for qid in sorted(det):
    pdfname, qnum = loc[qid]
    q = next(x for x in pdfdata[pdfname]['questions'] if x['qnum'] == qnum)
    own = crop(pdfname, q['images'], f'fig_{qid}') if q['images'] else []
    sh = group_files.get(qid, [])
    if not own and not sh:
        continue
    out.append(dict(編號=qid, 分類=det[qid]['分類'], 對應PDF=pdfname, PDF題號=qnum,
                    題組=('第%d~%d題' % group_of[qid]) if qid in group_of else '',
                    共用圖=';'.join(sh), 自有圖=';'.join(own),
                    圖片檔名=';'.join(sh + own),
                    題幹=re.sub(r'\s+', '', q['stem'])[:80]))

correct = {r['編號']: r['圖片檔名'] for r in out}

# ---- audit the current practice mapping ----
theirs = {r['編號']: os.path.basename((r.get('圖片檔名') or '').strip())
          for r in prac if (r.get('圖片檔名') or '').strip().lower() not in ('', 'none', 'null')}
qdir = os.path.join(PRAC, 'assets', 'q_images')
def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest() if os.path.exists(p) else None
h2q = collections.defaultdict(list)
for qid, fn in theirs.items():
    h = md5(os.path.join(qdir, fn))
    if h:
        h2q[h].append(qid)

rep = []
for qid in sorted(set(theirs) | set(correct)):
    h = md5(os.path.join(qdir, theirs[qid])) if qid in theirs else None
    shared = sorted(h2q.get(h, [])) if h else []
    grp = ('第%d~%d題' % group_of[qid]) if qid in group_of else ''
    if qid in theirs and qid not in correct:
        v = '❌ 錯配：此題在 PDF 中沒有圖，也不屬於任何題組'
    elif qid in correct and qid not in theirs:
        v = ('❌ 遺漏：屬於題組，需顯示共用圖' if qid in group_of and not
             next(x for x in out if x['編號'] == qid)['自有圖']
             else '❌ 遺漏：PDF 有圖但 CSV 未標記')
    elif len(shared) > 1:
        v = f'⚠️ 與其他 {len(shared)-1} 題共用同一檔，需確認是否為題組共用圖'
    else:
        v = '✅ 專屬檔案，題號對應正確'
    rep.append(dict(編號=qid, 分類=det[qid]['分類'], 題組=grp,
                    現況圖片檔=theirs.get(qid, '(無)'),
                    共用此檔的題號='、'.join(shared) if len(shared) > 1 else '',
                    正確圖片檔=correct.get(qid, '(此題不需圖)'), 判定=v,
                    題幹=re.sub(r'\s+', '', next(
                        x for x in pdfdata[loc[qid][0]]['questions']
                        if x['qnum'] == loc[qid][1])['stem'])[:70]))

def wr(name, data):
    with open(os.path.join(DST, name), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)

wr('07_正確圖片對應.csv', out)
wr('08_現況圖片對應稽核.csv', rep)

# ---- corrected question bank ----
img3 = {r['編號'] for r in csv.DictReader(
    open(os.path.join(DST, '03_圖片依賴題清單.csv'), encoding='utf-8-sig'))}
for r in prac:
    r['圖片檔名'] = ';'.join('figures/' + f for f in correct[r['編號']].split(';')) \
        if r['編號'] in correct else ''
    r['題組'] = ('第%d~%d題' % group_of[r['編號']]) if r['編號'] in group_of else ''
    r['圖片待人工確認'] = '是' if (r['編號'] in img3 and r['編號'] not in correct) else ''
wr('09_修正版題庫_含正確圖片對應.csv', prac)

c = collections.Counter(r['判定'].split('：')[0] for r in rep)
print('有圖題數(自有或題組共用):', len(out))
print('題組題數:', len(group_of), '| 圖檔數:', len(os.listdir(FIGDIR)))
for k, v in c.most_common():
    print(f'  {v:>3}  {k}')
