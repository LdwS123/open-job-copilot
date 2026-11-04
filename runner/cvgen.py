#!/usr/bin/env python3
"""ATS-friendly one-page CV generator (single column, real text, no images, clickable links, right-aligned dates).

Data-driven: everything comes from cv_data.json (copy ../cv_data.example.json, git-ignored). Facts are fixed; only the
headline, summary and skills emphasis change per "family" (e.g. sdr_bdr, account_manager) and per posting (tailor.py).

    python3 -I cvgen.py            # builds every family x language found in cv_data.json into output_dir

Layout: centred caps name, family subtitle, contact line, blue underlined links, ruled caps headings, role in bold with
the date right-aligned, italic company line, bullets. Font size shrinks 10.2 -> 7.6 pt until it fits ONE page.
"""
import json, os, re, sys
from xml.sax.saxutils import escape as E
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
BLUE = '#0563C1'
SEP = '  |  '
DEFAULT_HEAD = {
    'EN': dict(exp='PROFESSIONAL EXPERIENCE', edu='EDUCATION', skills='SKILLS & CERTIFICATIONS', add='LEADERSHIP & ADDITIONAL'),
    'FR': dict(exp='EXPÉRIENCE PROFESSIONNELLE', edu='FORMATION', skills='COMPÉTENCES & CERTIFICATIONS', add='LEADERSHIP & ACTIVITÉS COMPLÉMENTAIRES'),
}
LANG_LABEL = {'EN': 'Languages:', 'FR': 'Langues :'}


def load_data(path=None):
    path = path or os.environ.get('JOB_CV_DATA') or next(
        (p for p in (os.path.join(HERE, '..', 'cv_data.json'), os.path.join(HERE, '..', 'cv_data.example.json')) if os.path.exists(p)), None)
    if not path:
        raise SystemExit('cv_data.json not found: copy cv_data.example.json to cv_data.json and fill it with your true facts')
    return json.load(open(path, encoding='utf-8'))


DATA = load_data()
NAME = DATA['name']
CITY, COUNTRY = DATA.get('city', ''), DATA.get('country', '')
EMAIL, PHONE = DATA.get('email', ''), DATA.get('phone', '')
HOME = ', '.join(x for x in (CITY, COUNTRY) if x)
PHONE_MAIL = ' | '.join(x for x in (PHONE, EMAIL) if x)          # tailor.py puts a posting-specific location in front of this
CONTACT = ' | '.join(x for x in (HOME, PHONE, EMAIL) if x)
OUT = os.path.expanduser(os.environ.get('JOB_CV_DIR') or DATA.get('output_dir') or '~/job-copilot-cv')
# keep OUT free of spaces: the browser agent's file_upload tool refuses paths it cannot resolve (e.g. a folder named "x ")
PAGE = LETTER if str(DATA.get('page_size', 'A4')).lower() in ('letter', 'us letter') else A4
FAM = DATA.get('families', {})
LANGS = [k for k in DATA if re.fullmatch(r'[A-Z]{2}', k)]
URL = {l['label']: l['url'] for l in DATA.get('links', [])}
if EMAIL:
    URL[EMAIL] = 'mailto:' + EMAIL


def safe(s):
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')[:40] or 'x'


FILE_PREFIX = safe(NAME) + '_cv_'


def head_for(lang):
    h = dict(DEFAULT_HEAD.get(lang, DEFAULT_HEAD['EN']))
    h.update(DATA.get(lang, {}).get('headings', {}))
    return h


def _fonts():
    if 'Carlito' in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont('Carlito', os.path.join(FD, 'Carlito-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('Carlito-Bold', os.path.join(FD, 'Carlito-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('Carlito-Italic', os.path.join(FD, 'Lato-RegularItalic.ttf')))
    pdfmetrics.registerFontFamily('Carlito', normal='Carlito', bold='Carlito-Bold', italic='Carlito-Italic', boldItalic='Carlito-Bold')


def link(label, url=None):
    return '<a href="%s" color="%s"><u>%s</u></a>' % (url or URL[label], BLUE, E(label))


def linkify(s, urls):
    """escape s, then turn each {text: url} of `urls` into a clickable blue underlined link"""
    s = E(s)
    for text, url in urls.items():
        s = s.replace(E(text), link(text, url), 1)
    return s


def labelled(s):
    """'Label: text' -> bold label"""
    m = re.match(r'([^:]{2,45}?\s?:)\s(.*)$', s, re.S)
    return '<b>%s</b> %s' % (E(m.group(1)), E(m.group(2))) if m else E(s)


def build(fam, lang, out=None, apply_line=None, kw_line=None, contact=None):
    """apply_line / kw_line are used only by tailor.py (per-offer CV): one replacement sentence in the summary and one
    'matching skills' line at the top of SKILLS. Facts are never touched. Returns (path, font size used)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from pypdf import PdfReader
    _fonts()
    f = FAM[fam]
    fl = f.get(lang) or f['EN']
    title, lead, tail = fl['title'], fl.get('lead', ''), fl.get('tail', '')
    D = DATA[lang]
    H = head_for(lang)
    out = out or os.path.join(OUT, f'{FILE_PREFIX}{fam}_{lang}.pdf')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    PW, PH = PAGE
    LM = RM = 13 * mm
    W = PW - LM - RM - 12   # inner width of the frame (reportlab pads 6 pt each side) so rules, tables and text line up
    for size in [10.2 - 0.1 * i for i in range(27)]:   # 10.2 .. 7.6
        P = lambda n, **k: ParagraphStyle(n, **{'fontName': 'Carlito', 'bulletFontName': 'Carlito', **k})
        st = dict(
            name=P('n', fontName='Carlito-Bold', fontSize=size + 9, leading=size + 11, alignment=TA_CENTER),
            sub=P('s', fontSize=size + 0.6, leading=size + 2.4, alignment=TA_CENTER),
            ctr=P('c', fontSize=size - 0.2, leading=size + 1.4, alignment=TA_CENTER),
            h=P('h', fontName='Carlito-Bold', fontSize=size + 0.6, leading=size + 2.4, spaceBefore=5.5, spaceAfter=0.6),
            t=P('t', fontName='Carlito-Bold', fontSize=size, leading=size + 1.6),
            d=P('d', fontSize=size - 0.2, leading=size + 1.6, alignment=2),
            i=P('i', fontName='Carlito-Italic', fontSize=size - 0.2, leading=size + 1.3),
            b=P('b', fontSize=size - 0.2, leading=size + 1.4, leftIndent=9, bulletIndent=1, spaceBefore=0.4),
            p=P('p', fontSize=size - 0.2, leading=size + 1.5))

        def rule(after=1.5, before=0):
            return HRFlowable(width='100%', thickness=0.6, color=colors.black, spaceBefore=before, spaceAfter=after)

        def head(txt):
            return [Paragraph(E(txt), st['h']), rule(after=1.2)]

        def row(left_markup, date, before=2.8, lstyle='t'):
            if not date:
                p = Paragraph(left_markup, st[lstyle]); p.spaceBefore = before
                return p
            dw = stringWidth(date, 'Carlito', size - 0.2) + 8
            t = Table([[Paragraph(left_markup, st[lstyle]), Paragraph(E(date), st['d'])]], colWidths=[W - dw, dw])
            t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                   ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
            t.spaceBefore = before
            return t

        contact_s = contact or CONTACT
        S = [Paragraph(E(NAME.upper()), st['name']), Paragraph(E(title.replace(' | ', SEP)), st['sub']),
             Paragraph(linkify(contact_s.replace(' | ', SEP), {EMAIL: URL[EMAIL]} if EMAIL else {}), st['ctr'])]
        if DATA.get('links'):
            S.append(Paragraph(SEP.join(link(l['label'], l['url']) for l in DATA['links']), st['ctr']))
        S.append(rule(after=2.5, before=2))
        S.append(Paragraph(E(' '.join(x for x in (lead, D.get('core', ''), apply_line or tail) if x)), st['p']))

        def entries(items):
            out_ = []
            for e in items:
                urls = e.get('links', {})
                out_.append(row(E(e['role']), e.get('dates', '')))
                if e.get('company'):
                    out_.append(Paragraph(linkify(e['company'], urls), st['i']))
                for b in e.get('bullets', []):
                    out_.append(Paragraph(linkify(b, urls), st['b'], bulletText='•'))
            return out_

        S += head(H['exp']) + entries(D.get('experience', []))
        if D.get('education'):
            S += head(H['edu'])
            for e in D['education']:
                S.append(row('<b>%s</b>%s' % (E(e['school']), (' — ' + E(e['degree'])) if e.get('degree') else ''), e.get('dates', ''), before=1.6, lstyle='p'))
        S += head(H['skills'])
        if kw_line:
            S.append(Paragraph(labelled(kw_line), st['p']))
        for k in f.get('skills', []):
            if k in D.get('skills', {}):
                S.append(Paragraph(labelled(D['skills'][k]), st['p']))
        if D.get('certifications'):
            S.append(Paragraph(labelled(D['certifications']), st['p']))
        if D.get('languages'):
            S.append(Paragraph('<b>%s</b> %s' % (E(LANG_LABEL.get(lang, LANG_LABEL['EN'])), E(D['languages'])), st['p']))
        if D.get('additional'):
            S += head(H['add']) + entries(D['additional'])
        doc = SimpleDocTemplate(out, pagesize=PAGE, leftMargin=LM, rightMargin=RM, topMargin=11 * mm, bottomMargin=9 * mm,
                                title=f'{NAME} - CV', author=NAME)
        doc.build(S)
        if len(PdfReader(out).pages) == 1:
            return out, size
    raise SystemExit('does not fit on 1 page: %s %s (shorten some bullets)' % (fam, lang))


if __name__ == '__main__':
    for fam in FAM:
        for lang in LANGS:
            print(*build(fam, lang))
