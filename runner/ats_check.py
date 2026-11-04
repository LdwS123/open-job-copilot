#!/usr/bin/env python3
"""ATS parse check for the CV PDFs. Read-only, no network.

usage: python3 -I ats_check.py [folder-or-file ...]     (default: the output folder and its tailored/ sub-folder)

It imitates what an applicant-tracking parser needs from a PDF and flags anything that would make it fail:
  1. real selectable text (no scanned image), same text from two extraction modes, no garbled glyphs
  2. one column, reading order = visual order: name first, then contact, then the standard sections in order
  3. contact data parseable: one e-mail and one phone, within the header
  4. standard section headings on their own line, no images
  5. every experience/education line has a parseable date range on the same visual line
  6. fonts are standard, minimum font size (small text is flagged for humans)
  7. tailored files only: posting title + company are in the summary, location line is in the header, a true-keyword line exists
Writes ats_check_report.md and exits 1 if any file FAILS.
"""
import glob, os, re, sys
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvgen

R = os.path.dirname(os.path.abspath(__file__))
CVDIR = cvgen.OUT
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE = re.compile(r'\+?\d[\d\s().-]{7,}\d')
MONTHS = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|janv\.|févr\.|mars|avr\.|mai|juin|juil\.|août|sept\.|oct\.|nov\.|déc\.)\.?'
DATE = re.compile(r'(?:%s\s+)?(?:19|20)\d{2}\s*[–-]\s*(?:(?:%s\s+)?(?:19|20)\d{2}|Present|aujourd\'hui|present|présent)' % (MONTHS, MONTHS), re.I)
WINANSI_EXTRA = set('–—‘’“”•…€™')   # outside Latin-1 but inside WinAnsi


def sections(lang):
    """(required headings in order, optional headings) taken from the same data the generator uses"""
    h, d = cvgen.head_for(lang), cvgen.DATA.get(lang, {})
    req = [h['exp']] + ([h['edu']] if d.get('education') else []) + [h['skills']]
    return req + ([h['add']] if d.get('additional') else []), ()


def expected_dated(lang):
    d = cvgen.DATA.get(lang, {})
    return len([e for e in d.get('experience', []) + d.get('additional', []) + d.get('education', []) if e.get('dates')])


def text_modes(page):
    return page.extract_text() or '', page.extract_text(extraction_mode='layout') or ''


def font_sizes(page):
    sizes = []

    def visitor(text, cm, tm, font_dict, font_size):
        if text.strip():
            sizes.append(round(font_size * (abs(tm[0]) if tm and tm[0] else 1), 1) if font_size else 0)
    page.extract_text(visitor_text=visitor)
    return sizes


def check(path):
    name = os.path.basename(path)
    m = re.match(re.escape(cvgen.FILE_PREFIX) + r'(.+)_([A-Z]{2})\.pdf$', name)
    lang = m.group(2) if m and m.group(2) in cvgen.LANGS else 'EN'
    tailored = '/tailored/' in path
    fails, warns, info = [], [], {}
    try:
        rd = PdfReader(path)
    except Exception as e:
        return dict(file=name, tailored=tailored, fails=['unreadable PDF: %s' % e], warns=[], info={})
    info['pages'] = len(rd.pages)
    if len(rd.pages) > 2:
        fails.append('%d pages (ATS summaries expect 1-2)' % len(rd.pages))
    page = rd.pages[0]
    txt, layout = text_modes(page)
    info['chars'] = len(txt)
    if len(txt) < 1000:
        fails.append('too little extractable text (%d chars): scanned image or broken fonts' % len(txt))
    if '�' in txt or '(cid:' in txt:
        fails.append('garbled glyphs in extracted text')
    w1 = set(re.findall(r'\w{5,}', txt.lower())); w2 = set(re.findall(r'\w{5,}', layout.lower()))
    if w1 and len(w1 & w2) / len(w1) < 0.97:
        warns.append('two extraction modes disagree (%.0f%% shared words)' % (100 * len(w1 & w2) / len(w1)))
    res = page.get('/Resources') or {}
    xo = res.get('/XObject') or {}
    if any((xo[k].get_object().get('/Subtype') == '/Image') for k in xo):
        fails.append('contains an image (ATS cannot read it)')
    fonts = {str(v.get_object().get('/BaseFont')) for k, v in (res.get('/Font') or {}).items()}
    info['fonts'] = sorted(fonts)
    bad = [f for f in fonts if not re.search(r'Helvetica|Arial|Times|Calibri|Carlito|Lato|Liberation|DejaVu', f)]
    if bad:
        warns.append('unusual fonts: %s' % bad)
    sizes = [s for s in font_sizes(page) if s]
    if sizes:
        info['min_font'] = min(sizes)
        if min(sizes) < 7:
            fails.append('font %.1f pt: too small even for parsers that flag it' % min(sizes))
        elif min(sizes) < 8:
            warns.append('smallest font %.1f pt (hard to read for a human recruiter)' % min(sizes))
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    if not lines or lines[0].lower() != cvgen.NAME.lower():
        fails.append('first line is not the candidate name: %r' % (lines[0] if lines else None))
    head = ' '.join(lines[:6])
    emails = EMAIL.findall(head)
    if cvgen.EMAIL and len(set(emails)) != 1:
        fails.append('expected exactly 1 e-mail in the header, found %s' % sorted(set(emails)))
    if cvgen.PHONE and not PHONE.search(head):
        fails.append('phone number not parseable in the header')
    for l in cvgen.DATA.get('links', []):
        if 'linkedin' in l['label'] and 'linkedin.com/in/' not in head:
            warns.append('no LinkedIn URL in the header')
    req, _ = sections(lang)
    pos = []
    for s in req:
        idx = [i for i, l in enumerate(lines) if l == s]
        if not idx:
            fails.append('missing standard heading %s' % s)
        else:
            pos.append((idx[0], s))
    if [s for _, s in sorted(pos)] != [s for _, s in pos]:
        fails.append('sections are out of order (multi-column or layout problem)')
    # dates are right-aligned: in the layout (visual-line) extraction the title and its date must sit on the SAME line
    llines = [l.strip() for l in layout.splitlines() if l.strip()]
    dated = [l for l in llines if DATE.search(l)]
    alone = [l for l in dated if len(DATE.sub('', l).strip()) < 3]
    if alone:
        warns.append('date range alone on a line (title and date not on the same visual line): %s' % alone[:2])
    info['dated_entries'] = len(dated)
    need = expected_dated(lang)
    if need and len(dated) < max(1, int(need * 0.75)):
        fails.append('only %d dated entries found (expected about %d)' % (len(dated), need))
    badyear = [l[:60] for l in llines if re.search(r'\b(19|20)\d{2}\s*[–-]', l) and not DATE.search(l)]
    if badyear:
        warns.append('date range not parseable on: %s' % badyear[:2])
    nlinks = sum(1 for a in (page.get('/Annots') or []) if '/URI' in (a.get_object().get('/A') or {}))
    info['links'] = nlinks
    if cvgen.DATA.get('links') and nlinks < len(cvgen.DATA['links']):
        warns.append('only %d clickable links (expected at least %d)' % (nlinks, len(cvgen.DATA['links'])))
    odd = sorted({c for c in txt if ord(c) > 255 and c not in WINANSI_EXTRA})
    if odd:
        warns.append('characters outside WinAnsi: %s' % odd)
    if tailored:
        body = ' '.join(lines)
        slug = m.group(1) if m else ''
        hx = [i for i, l in enumerate(lines) if l == req[0]]
        summary = ' '.join(lines[4:hx[0]]) if hx else ''   # no heading above the summary: block between header and first section
        words = [w for w in re.split(r'_', slug) if len(w) > 2]
        hit = [w for w in words if w.lower() in summary.lower()]
        info['slug_words_in_summary'] = '%d/%d' % (len(hit), len(words))
        if words and len(hit) < max(1, len(words) // 2):
            fails.append('posting title/company words not found in the summary (%d/%d)' % (len(hit), len(words)))
        if cvgen.CITY and cvgen.CITY not in ' '.join(lines[:4]):
            fails.append('location line missing in the header')
        if re.search(r'Matching this role|En lien avec ce poste', body):
            info['kw_line'] = True
        else:
            warns.append('no matching-keywords line (no true keyword matched this posting)')
    return dict(file=name, tailored=tailored, fails=fails, warns=warns, info=info)


def main():
    args = sys.argv[1:] or [CVDIR, os.path.join(CVDIR, 'tailored')]
    files = []
    for a in args:
        files += [a] if a.endswith('.pdf') else sorted(glob.glob(os.path.join(a, '*.pdf')))
    res = [check(f) for f in files]
    nf = sum(1 for r in res if r['fails']); nw = sum(1 for r in res if r['warns'] and not r['fails'])
    out = ['# ATS parse check', '', '- Files checked: %d | PASS: %d (of which with warnings: %d) | FAIL: %d' % (
        len(res), len(res) - nf, nw, nf), '']
    for r in res:
        st = 'FAIL' if r['fails'] else ('WARN' if r['warns'] else 'PASS')
        out.append('%s  %s%s  [%s]' % (st, '(tailored) ' if r['tailored'] else '', r['file'],
                                       ', '.join('%s=%s' % kv for kv in r['info'].items() if kv[0] in ('pages', 'chars', 'min_font', 'dated_entries', 'links'))))
        out += ['      FAIL: ' + x for x in r['fails']] + ['      warn: ' + x for x in r['warns']]
    rep = '\n'.join(out)
    open(os.path.join(R, 'ats_check_report.md'), 'w').write(rep)
    print(rep)
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
