# -*- coding: utf-8 -*-
"""Extract 50 questions from each iPAS exam PDF, with image attribution."""
import fitz, re, json, os, glob, collections, sys

SRC = r"D:\ai-antigravity\ipas-aiap\official_sources"
OUT = os.path.dirname(os.path.abspath(__file__))

EXAM_PDFS = [f for f in sorted(os.listdir(SRC))
             if f.endswith('.pdf') and ('公告' in f or '當次試題' in f) and '學習指引' not in f and '簡章' not in f]

HDR_PAT = [
    re.compile(r'公告試題】'),
    re.compile(r'^第[一二三四]科[：:]'),
    re.compile(r'考試日期'),
    re.compile(r'^第\s*\d+\s*頁，共\s*\d+\s*頁'),
    re.compile(r'^一、選擇題'),
    re.compile(r'以下空白'),          # end-of-paper marker
    re.compile(r'^\s*$'),
]

def boilerplate(doc):
    """Block texts repeating on a large share of pages are page furniture.

    Detected rather than hard-coded because the layout varies between papers:
    the answer-column label is one block ('答案 題目') in most, split into
    vertical '答'/'案'/'題目' blocks in others, and flips to '題目答案'
    part-way through one paper -- so no single literal covers them all.
    """
    cnt = collections.Counter()
    for p in doc:
        for b in p.get_text('blocks'):
            if b[6] != 0:
                continue
            t = re.sub(r'\s+', '', b[4])
            if t and len(t) <= 60:
                cnt[t] += 1
    return {t for t, n in cnt.items() if n / max(1, len(doc)) >= 0.35}

def is_header(t, boiler):
    s = re.sub(r'\s+', ' ', t).strip()
    s2 = re.sub(r'\s+', '', t)
    if s2 in boiler:
        return True
    return any(p.search(s) or p.search(s2) for p in HDR_PAT)

def watermark_boxes(doc):
    """Images whose (w,h,rounded bbox) repeat on >=60% of pages are page furniture."""
    cnt = collections.Counter()
    for p in doc:
        for x in p.get_images(full=True):
            try:
                bb = p.get_image_bbox(x)
            except Exception:
                continue
            cnt[(x[2], x[3], round(bb.x0), round(bb.y0), round(bb.x1), round(bb.y1))] += 1
    thr = max(2, int(len(doc) * 0.6))
    return {k for k, v in cnt.items() if v >= thr}

def parse_pdf(path):
    doc = fitz.open(path)
    wm = watermark_boxes(doc)
    boiler = boilerplate(doc)

    # ---- collect body blocks in reading order, keeping (page, y) ----
    items = []          # (page, y0, y1, text)
    content_imgs = []   # (page, y0, y1, w, h)
    for pno, page in enumerate(doc):
        blocks = [b for b in page.get_text('blocks') if b[6] == 0]
        blocks.sort(key=lambda b: (round(b[1], 1), b[0]))
        for x0, y0, x1, y1, txt, _, _ in blocks:
            if is_header(txt, boiler):
                continue
            items.append((pno, y0, y1, txt))
        for x in page.get_images(full=True):
            try:
                bb = page.get_image_bbox(x)
            except Exception:
                continue
            key = (x[2], x[3], round(bb.x0), round(bb.y0), round(bb.x1), round(bb.y1))
            if key in wm:
                continue
            content_imgs.append((pno, bb.y0, bb.y1, x[2], x[3]))

    # ---- build one text stream with char-offset -> (page,y) map ----
    stream, spans = [], []
    pos = 0
    for pno, y0, y1, txt in items:
        stream.append(txt)
        spans.append((pos, pos + len(txt), pno, y0, y1))
        pos += len(txt)
    full = ''.join(stream)

    def loc(off):
        for s, e, pno, y0, y1 in spans:
            if s <= off < e:
                return pno, y0, y1
        return spans[-1][2], spans[-1][3], spans[-1][4] if spans else (0, 0, 0)

    # ---- split into questions: answer letter, then "N." ----
    # NB: official PDFs mix halfwidth/fullwidth letters, and sometimes put the
    # stem on the same line as "N." -- both variants must be accepted.
    # ...the trailing "." after the question number is sometimes absent, and the
    # answer letter sometimes shares a line with the number ("Ｂ 40 請參考附圖").
    # Anchoring the letter to line start + requiring numbers to run 1,2,3,...
    # keeps this loose pattern from firing inside option text.
    QSTART = re.compile(r'(?:^|\n)[ \t]*([A-DＡ-Ｄ])[ \t]*\n?[ \t]*([0-9０-９]{1,2})\.?[ \t]*\n?[ \t]*')
    OPTMARK = re.compile(r'[(（]([A-DＡ-Ｄ])[)）]')

    def fw(s):
        return ''.join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)

    # keep only the strictly increasing 1,2,3,... run -- guards against a bare
    # "<letter>\n<number>" pattern appearing inside option text
    starts, expect = [], 1
    for m in QSTART.finditer(full):
        if int(fw(m.group(2))) == expect:
            starts.append((m.start(), m.end(), fw(m.group(1)), expect))
            expect += 1

    qs = []
    for i, (off, hend, letter, num) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(full)
        body = full[hend:end]

        # options: keep only the first monotonic A,B,C,D run
        seq, want = [], 'A'
        for m in OPTMARK.finditer(body):
            if fw(m.group(1)) == want:
                seq.append(m)
                want = chr(ord(want) + 1)
                if want > 'D':
                    break
        stem = body[:seq[0].start()] if seq else body
        opts = []
        for j, m in enumerate(seq):
            oe = seq[j + 1].start() if j + 1 < len(seq) else len(body)
            opts.append(body[m.end():oe])

        p0, y0, _ = loc(hend)
        p1, _, y1 = loc(max(off, end - 1))
        imgs = [dict(page=ip + 1, w=w, h=h) for ip, iy0, iy1, w, h in content_imgs
                if (ip > p0 or (ip == p0 and iy1 > y0)) and (ip < p1 or (ip == p1 and iy0 < y1))]

        qs.append(dict(qnum=num, answer_letter=letter, stem=stem, options=opts,
                       n_options=len(opts), images=imgs, fullwidth_answer=(letter != full[off:hend].strip()[:1]),
                       page_start=p0 + 1, page_end=p1 + 1, raw=body))

    npg = len(doc)
    doc.close()
    return dict(pdf=os.path.basename(path), n_pages=npg,
                questions=qs, n_content_images=len(content_imgs))

result = {}
for f in EXAM_PDFS:
    r = parse_pdf(os.path.join(SRC, f))
    result[f] = r
    bad = [q['qnum'] for q in r['questions'] if q['n_options'] != 4]
    nums = [q['qnum'] for q in r['questions']]
    print(f"{len(r['questions']):>3} q | opts!=4: {bad} | seq_ok={nums == list(range(1, 51))} | imgs={r['n_content_images']} | {f[:45]}")

with open(os.path.join(OUT, 'pdf_extracted.json'), 'w', encoding='utf-8') as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)
print('WROTE pdf_extracted.json')
