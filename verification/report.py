# -*- coding: utf-8 -*-
"""Classify every CSV/PDF difference and emit the checklist deliverables."""
import csv, json, os, re, difflib, collections, unicodedata, fitz

SRC = r"D:\ai-antigravity\ipas-aiap\official_sources"
DST = r"D:\ai-antigravity\ipas-aiap\verification"
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(DST, exist_ok=True)

pdfdata = json.load(open(os.path.join(HERE, 'pdf_extracted.json'), encoding='utf-8'))
rows = list(csv.DictReader(open(os.path.join(SRC, 'FALO-IPAS-AIAP-20260802.csv'), encoding='utf-8-sig')))

PUNCT = {ord(a): b for a, b in [
    ('「', '"'), ('」', '"'), ('『', '"'), ('』', '"'), ('“', '"'), ('”', '"'),
    ('‘', "'"), ('’', "'"), ('—', '-'), ('–', '-'), ('―', '-'), ('‒', '-'),
    ('−', '-'), ('‧', '.'), ('·', '.'), ('・', '.'), ('、', ','), ('。', '.')]}
OPT_PREFIX = re.compile(r'^[\s(（]*[1-4A-Da-dＡ-Ｄ][)）]\s*')
FIG_KW = re.compile(r'下圖|附圖|如圖|圖中|上圖|右圖|左圖|下表|附表|上表|程式碼|虛擬程式|pseudocode|執行結果|如下所示', re.I)
BAD_CP = re.compile(r'[\uFFFD\uE000-\uF8FF\uF900-\uFAFF]')
LEAK = re.compile(r'答案\s*題目|題目\s*答案|第[一二三]科[：:]\s*(?:人工智慧|生成式|大數據|機器學習)'
                  r'|能力鑑定【公告試題】|考試日期|第\s*\d+\s*頁，共\s*\d+\s*頁|以下空白')

def norm(s):
    s = unicodedata.normalize('NFKC', s or '').translate(PUNCT)
    return re.sub(r'\s+', '', s).strip('；;，,。.、 \u3000')

def strip_opt(s):
    return OPT_PREFIX.sub('', (s or '').strip(), count=1)

def key(s):
    return re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', s or '')

disk = set(os.listdir(SRC))
pdf_names = list(pdfdata)
def resolve(d):
    h = [p for p in pdf_names if key(p).startswith(key(d))]
    return h[0] if len(h) == 1 else None

by_doc = collections.defaultdict(list)
for r in rows:
    by_doc[r['文件名稱']].append(r)
ordinal = {}
for doc, rs in by_doc.items():
    for i, r in enumerate(sorted(rs, key=lambda x: x['編號']), 1):
        ordinal[r['編號']] = i

def classify(a, b, has_img, leaked):
    ins = dele = rep = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == 'insert':
            ins += j2 - j1
        elif tag == 'delete':
            dele += i2 - i1
        elif tag == 'replace':
            rep += max(i2 - i1, j2 - j1)
    tot = ins + dele + rep
    if leaked:
        cat = 'C4 頁首文字混入'
    elif has_img and ins > dele:
        cat = 'C1 圖片內容以文字補寫'
    elif dele >= 15 and dele > ins * 2:
        cat = 'C2 內容刪節'
    elif has_img:
        cat = 'C3 圖片題內容不完整'
    elif tot <= 3:
        cat = 'C5 字元層級瑕疵'
    else:
        cat = 'C6 文字改寫'
    return cat, ins, dele, rep

detail, imgrows = [], []
catcount = collections.Counter()

for r in rows:
    qid, real = r['編號'], resolve(r['文件名稱'])
    q = {x['qnum']: x for x in pdfdata[real]['questions']}[ordinal[qid]]
    has_img = bool(q['images']) or bool(FIG_KW.search(q['stem'] + ''.join(q['options'])))
    l3, other, cats, notes = [], [], set(), []

    # --- L3 content ---
    exp = str('ABCD'.index(q['answer_letter']) + 1)
    ans_ok = r['正確答案'] == exp
    if not ans_ok:
        l3.append(f"答案錯誤：PDF={q['answer_letter']}(應為{exp})，CSV={r['正確答案']}")
        cats.add('C0 答案錯誤')

    fields = [('題幹', norm(q['stem']), norm(r['題目']), r['題目'])] + \
             [(f'選項{i}', norm(strip_opt(q['options'][i-1])), norm(strip_opt(r[f'選項{i}'])), r[f'選項{i}'])
              for i in range(1, 5)]
    for name, a, b, rawcsv in fields:
        if a != b:
            cat, ins, dele, rep = classify(a, b, has_img, bool(LEAK.search(rawcsv or '')))
            l3.append(f'{name}不符（{cat[:2]}：刪{dele}/增{ins}/改{rep}）')
            cats.add(cat)
            if not notes:
                notes.append(f'PDF「{a[:80]}」｜CSV「{b[:80]}」')

    pn = [norm(strip_opt(o)) for o in q['options']]
    cn = [norm(strip_opt(r[f'選項{i}'])) for i in range(1, 5)]
    if pn != cn and sorted(pn) == sorted(cn):
        l3.append('選項順序遭調換')
        cats.add('C0 選項順序')

    # --- L1 traceability / L2 numbering / L4 display ---
    trace_ok = r['文件名稱'] in disk
    if not trace_ok:
        other.append('L1 文件名稱無法對應實體檔')
    num_ok = int(r['題號']) == q['qnum']
    if not num_ok:
        other.append(f"L2 題號與PDF印刷題號不符(CSV={int(r['題號'])}/PDF={q['qnum']})")

    disp = []
    for fld in ['題目', '選項1', '選項2', '選項3', '選項4']:
        v = r[fld] or ''
        if LEAK.search(v):
            disp.append(f'{fld}混入頁首文字')
        if BAD_CP.search(v):
            disp.append(f'{fld}含亂碼字元')
        if '  ' in v.replace('\u3000', ' '):
            disp.append(f'{fld}多餘連續空白')
    for i in range(1, 5):
        if not OPT_PREFIX.match((r[f'選項{i}'] or '').strip()):
            disp.append(f'選項{i}缺少({i})標記')
    other += [f'L4 {d}' for d in disp]

    for c in cats:
        catcount[c] += 1

    detail.append(dict(
        編號=qid, 分類=r['分類'], 對應PDF=real, PDF題號=q['PDF' if False else 'qnum'], CSV題號=int(r['題號']),
        內容判定='PASS' if not l3 else 'FAIL',
        答案判定='PASS' if ans_ok else 'FAIL',
        溯源判定='PASS' if trace_ok else 'FAIL',
        題號判定='PASS' if num_ok else 'FAIL',
        顯示判定='PASS' if not disp else 'FAIL',
        圖片依賴='是' if has_img else '否', 內嵌圖片數=len(q['images']),
        差異類型='; '.join(sorted(cats)) or '-',
        內容差異明細=' | '.join(l3) or '完全一致',
        其他問題=' | '.join(other) or '-',
        差異摘要=notes[0] if notes else ''))

    if has_img:
        imgrows.append(dict(
            編號=qid, 分類=r['分類'], 對應PDF=real, PDF題號=q['qnum'], PDF頁碼=q['page_start'],
            內嵌圖片數=len(q['images']),
            圖片尺寸='; '.join(f"{i['w']}x{i['h']}" for i in q['images']) or '(無內嵌點陣圖：向量圖或文字表格)',
            題幹提及圖表='是' if FIG_KW.search(q['stem'] + ''.join(q['options'])) else '否',
            CSV是否文字補寫='是' if 'C1 圖片內容以文字補寫' in detail[-1]['差異類型'] else '否',
            內容判定=detail[-1]['內容判定'],
            風險='高：CSV 無圖，作答資訊不足' if not detail[-1]['差異類型'].startswith('C1') else '中：CSV 已文字補寫，需人工核對正確性',
            PDF題幹=re.sub(r'\s+', '', q['stem'])[:100]))

# ---- L1 file-level table (12 exam PDFs) ----
l1 = []
for doc, rs in sorted(by_doc.items()):
    real = resolve(doc)
    d = [x for x in detail if x['對應PDF'] == real and x['編號'] in {y['編號'] for y in rs}]
    ids = {y['編號'] for y in rs}
    d = [x for x in detail if x['編號'] in ids]
    l1.append(dict(對應PDF=real, 分類=rs[0]['分類'], PDF頁數=pdfdata[real]['n_pages'],
                   CSV題數=len(rs), PDF題數=len(pdfdata[real]['questions']),
                   題數相符='是' if len(rs) == len(pdfdata[real]['questions']) else '否',
                   文件名稱可溯源='是' if doc in disk else '否',
                   內容PASS=sum(1 for x in d if x['內容判定'] == 'PASS'),
                   內容FAIL=sum(1 for x in d if x['內容判定'] == 'FAIL'),
                   CSV文件名稱=doc))

# ---- L1b: the 8 non-exam PDFs (no CSV counterpart -> health check only) ----
other_pdfs = []
for f in sorted(disk):
    if not f.endswith('.pdf') or f in pdfdata:
        continue
    try:
        d = fitz.open(os.path.join(SRC, f))
        txt = ''.join(p.get_text() for p in d)
        # U+E000-F8FF here is Wingdings/Symbol bullet glyphs, not corruption;
        # only U+FFFD is genuine mojibake.
        pua = len(re.findall(r'[-]', txt))
        compat = len(re.findall(r'[豈-﫿]', txt))
        other_pdfs.append(dict(檔名=f, 頁數=len(d), 可開啟='是', 已加密='是' if d.is_encrypted else '否',
                               文字層字數=len(txt.strip()),
                               文字層可抽取='是' if len(txt.strip()) > 500 else '否(疑為掃描檔)',
                               真亂碼U_FFFD='是' if '�' in txt else '否',
                               符號字型字元數=pua, CJK相容字數=compat,
                               備註='符號字型字元為項目符號，非亂碼' if pua else '',
                               與CSV對應='無（非試題檔，不納入內容比對）'))
        d.close()
    except Exception as e:
        other_pdfs.append(dict(檔名=f, 頁數=0, 可開啟='否', 已加密='?', 文字層字數=0,
                               文字層可抽取='否', 真亂碼U_FFFD='?', 符號字型字元數=0,
                               CJK相容字數=0, 備註='', 與CSV對應=f'開啟失敗: {e}'))

def wr(name, data):
    with open(os.path.join(DST, name), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0]))
        w.writeheader(); w.writerows(data)

wr('02_逐題檢查明細.csv', detail)
wr('03_圖片依賴題清單.csv', imgrows)
wr('04_PDF檔案層檢查.csv', l1 + [{}] * 0)
wr('05_其他PDF健檢.csv', other_pdfs)

stats = dict(
    total=len(detail),
    content=collections.Counter(d['內容判定'] for d in detail),
    ans=collections.Counter(d['答案判定'] for d in detail),
    trace=collections.Counter(d['溯源判定'] for d in detail),
    num=collections.Counter(d['題號判定'] for d in detail),
    disp=collections.Counter(d['顯示判定'] for d in detail),
    cats=catcount,
    by_subject={c: collections.Counter(d['內容判定'] for d in detail if d['分類'] == c)
                for c in ['A1', 'A2', 'B1', 'B2', 'B3']},
    n_img=len(imgrows), n_img_embed=sum(1 for i in imgrows if i['內嵌圖片數'] > 0),
    n_img_written=sum(1 for i in imgrows if i['CSV是否文字補寫'] == '是'),
    l1=l1, other=other_pdfs,
    clean=sum(1 for d in detail if d['內容判定'] == 'PASS' and d['顯示判定'] == 'PASS'
              and d['溯源判定'] == 'PASS' and d['題號判定'] == 'PASS'),
)
json.dump(stats, open(os.path.join(HERE, 'final.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('content', dict(stats['content']), 'clean', stats['clean'])
print('cats', dict(catcount))
