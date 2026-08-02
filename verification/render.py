# -*- coding: utf-8 -*-
"""Render each flagged question's original PDF region to a PNG data URI."""
import fitz, json, os, csv, io, re, shutil

SRC = r"D:\ai-antigravity\ipas-aiap\official_sources"
DST = r"D:\ai-antigravity\ipas-aiap\verification"
IMGDIR = os.path.join(DST, 'shots')
HERE = os.path.dirname(os.path.abspath(__file__))
ZOOM = 1.7
PAD = 14

# Images live as separate files, not base64: a single 11 MB self-contained page
# never finished parsing in the browser. With loading="lazy" and only the current
# item in the DOM, just the visible question's shots are ever fetched.
shutil.rmtree(IMGDIR, ignore_errors=True)
os.makedirs(IMGDIR, exist_ok=True)

pdfdata = json.load(open(os.path.join(HERE, 'pdf_extracted.json'), encoding='utf-8'))
img = list(csv.DictReader(open(os.path.join(DST, '03_圖片依賴題清單.csv'), encoding='utf-8-sig')))
det = {r['編號']: r for r in csv.DictReader(open(os.path.join(DST, '02_逐題檢查明細.csv'), encoding='utf-8-sig'))}
rows = {r['編號']: r for r in csv.DictReader(open(os.path.join(SRC, 'FALO-IPAS-AIAP-20260802.csv'), encoding='utf-8-sig'))}

docs = {}
def doc(p):
    if p not in docs:
        docs[p] = fitz.open(os.path.join(SRC, p))
    return docs[p]

def clean(s):
    return re.sub(r'[ \t]*\n[ \t]*', '', (s or '')).strip(' \u3000；;')

out, total = [], 0
for i in img:
    pdfname = i['對應PDF']
    d = doc(pdfname)
    q = next(x for x in pdfdata[pdfname]['questions'] if x['qnum'] == int(i['PDF題號']))
    p0, p1 = q['page_start'] - 1, q['page_end'] - 1
    shots = []
    for pno in range(p0, p1 + 1):
        page = d[pno]
        top = max(0, q['y_start'] - PAD) if pno == p0 else 0
        bot = min(page.rect.y1, q['y_end'] + PAD) if pno == p1 else page.rect.y1 - 28
        if bot - top < 12:
            continue
        clip = fitz.Rect(24, top, page.rect.x1 - 16, bot)
        px = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
        b = px.tobytes('png')
        total += len(b)
        fn = f"{i['編號']}_p{pno+1}.png"
        open(os.path.join(IMGDIR, fn), 'wb').write(b)
        shots.append(dict(page=pno + 1, w=px.width, h=px.height, src='shots/' + fn))

    r, dd = rows[i['編號']], det[i['編號']]
    out.append(dict(
        id=i['編號'], cat=i['分類'], tier=('A' if int(i['內嵌圖片數']) > 0 and i['CSV是否文字補寫'] == '否'
                                        else 'B' if int(i['內嵌圖片數']) > 0 else 'C'),
        pdf=pdfname, pdfq=int(i['PDF題號']), csvq=int(r['題號']), page=i['PDF頁碼'],
        nimg=int(i['內嵌圖片數']), imgsize=i['圖片尺寸'],
        contentVerdict=dd['內容判定'], diffType=dd['差異類型'], diffDetail=dd['內容差異明細'],
        otherIssue=dd['其他問題'],
        pdfStem=clean(q['stem']), pdfOpts=[clean(o) for o in q['options']],
        pdfAns='ABCD'.index(q['answer_letter']) + 1,
        csvStem=(r['題目'] or '').strip(), csvOpts=[(r[f'選項{k}'] or '').strip() for k in range(1, 5)],
        csvAns=int(r['正確答案']), shots=shots))

json.dump(out, open(os.path.join(HERE, 'review_data.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{len(out)} items, {sum(len(o["shots"]) for o in out)} renders, {total/1048576:.1f} MB of PNG')
