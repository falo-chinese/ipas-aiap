# -*- coding: utf-8 -*-
"""Rebuild the question->figure mapping from PDF coordinates, and diff it
against the mapping currently in practice/FALO-IPAS-AIAP-20260802.csv."""
import fitz, json, os, csv, io, re, collections, hashlib, shutil

SRC = r"D:\ai-antigravity\ipas-aiap\official_sources"
DST = r"D:\ai-antigravity\ipas-aiap\verification"
PRAC = r"D:\ai-antigravity\ipas-aiap\practice"
FIGDIR = os.path.join(DST, 'figures')
HERE = os.path.dirname(os.path.abspath(__file__))
ZOOM = 3.0
PAD = 6

pdfdata = json.load(open(os.path.join(HERE, 'pdf_extracted.json'), encoding='utf-8'))
det = {r['編號']: r for r in csv.DictReader(open(os.path.join(DST, '02_逐題檢查明細.csv'), encoding='utf-8-sig'))}
prac = list(csv.DictReader(open(os.path.join(PRAC, 'FALO-IPAS-AIAP-20260802.csv'), encoding='utf-8-sig')))
img3 = {r['編號']: r for r in csv.DictReader(open(os.path.join(DST, '03_圖片依賴題清單.csv'), encoding='utf-8-sig'))}

shutil.rmtree(FIGDIR, ignore_errors=True)
os.makedirs(FIGDIR, exist_ok=True)

# 編號 -> (pdf, qnum), taken from the verified detail sheet
loc = {qid: (r['對應PDF'], int(r['PDF題號'])) for qid, r in det.items()}

docs = {}
def doc(p):
    if p not in docs:
        docs[p] = fitz.open(os.path.join(SRC, p))
    return docs[p]

out = []
for qid in sorted(det):
    pdfname, qnum = loc[qid]
    q = next(x for x in pdfdata[pdfname]['questions'] if x['qnum'] == qnum)
    if not q['images']:
        continue
    # Union of this question's own figure boxes, per page. Attribution is by
    # coordinate containment inside the question's vertical span -- which is
    # what makes neighbouring questions impossible to mix up.
    bypage = collections.defaultdict(list)
    for im in q['images']:
        bypage[im['page']].append(im)
    d = doc(pdfname)
    files = []
    for pg, ims in sorted(bypage.items()):
        page = d[pg - 1]
        x0 = max(0, min(i['x0'] for i in ims) - PAD)
        y0 = max(0, min(i['y0'] for i in ims) - PAD)
        x1 = min(page.rect.x1, max(i['x1'] for i in ims) + PAD)
        y1 = min(page.rect.y1, max(i['y1'] for i in ims) + PAD)
        px = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=fitz.Rect(x0, y0, x1, y1))
        suffix = '' if len(bypage) == 1 else f'_p{pg}'
        fn = f'{qid}{suffix}.png'
        open(os.path.join(FIGDIR, fn), 'wb').write(px.tobytes('png'))
        files.append(fn)
    out.append(dict(編號=qid, 分類=det[qid]['分類'], 對應PDF=pdfname, PDF題號=qnum,
                    圖片數=len(q['images']), 圖片檔名=';'.join(files),
                    題幹=re.sub(r'\s+', '', q['stem'])[:80]))

correct = {r['編號']: r['圖片檔名'] for r in out}

# ---- diff against the practice CSV ----
theirs = {}
for r in prac:
    v = (r.get('圖片檔名') or '').strip()
    if v and v.lower() not in ('none', 'null'):
        theirs[r['編號']] = os.path.basename(v)

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest() if os.path.exists(p) else None

qdir = os.path.join(PRAC, 'assets', 'q_images')
h2q = collections.defaultdict(list)
for qid, fn in theirs.items():
    h = md5(os.path.join(qdir, fn))
    if h:
        h2q[h].append(qid)

rep = []
for qid in sorted(set(theirs) | set(correct)):
    h = md5(os.path.join(qdir, theirs[qid])) if qid in theirs else None
    shared = sorted(h2q.get(h, [])) if h else []
    if qid in theirs and qid not in correct:
        v = '❌ 錯配：此題在 PDF 中沒有任何圖片'
    elif qid in correct and qid not in theirs:
        v = '❌ 遺漏：PDF 有圖但 CSV 未標記'
    elif len(shared) > 1:
        v = f'⚠️ 與其他題共用同一檔（{len(shared)} 題共用），至多一題正確'
    else:
        v = '✅ 專屬檔案，題號對應正確'
    rep.append(dict(編號=qid, 分類=det[qid]['分類'],
                    現況圖片檔=theirs.get(qid, '(無)'),
                    共用此檔的題號='、'.join(shared) if len(shared) > 1 else '',
                    PDF實際圖片數=(len(correct[qid].split(';')) if qid in correct else 0),
                    正確圖片檔=correct.get(qid, '(此題不需圖)'),
                    判定=v, 題幹=(det[qid].get('差異摘要') or '')[:0] or
                    re.sub(r'\s+', '', next(x for x in pdfdata[loc[qid][0]]['questions']
                                            if x['qnum'] == loc[qid][1])['stem'])[:70]))

def wr(name, data):
    with open(os.path.join(DST, name), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)

wr('07_正確圖片對應.csv', out)
wr('08_現況圖片對應稽核.csv', rep)

c = collections.Counter(r['判定'][:2] for r in rep)
print(f'PDF 實際有圖題數: {len(out)}  (共 {sum(r["圖片數"] for r in out)} 張)')
print(f'現況標記: {len(theirs)}')
print('稽核:', dict(c))
print('已輸出 figures/', len(os.listdir(FIGDIR)), '個檔案')
