#!/usr/bin/env python3
"""Per-offer ATS resume:
  python3 -I tailor.py --family sdr_bdr --lang EN --role "Sales Development Representative" --company "Acme" \
       --city Paris --country France --keywords "outbound,pipeline,HubSpot,cold calling,Salesforce"

Takes the keywords the posting asks for, KEEPS ONLY the ones that are true for you (the `true_skills` allowlist in
cv_data.json, built from YOUR facts), and writes a one-page PDF to the output folder with:
  - the posting's job title in the summary ("Applying for the <role> position at <company>")
  - a first SKILLS line "Matching this role: ..." using the posting's own wording
  - a location line that matches the posting (home city / "open to remote work" / "open to relocation to <City>")
Everything else (dates, employers, numbers) is the unchanged base CV. Keywords that are not true are DROPPED and printed,
never added. Prints  CV <path> / LOCATION LINE / KEPT / DROPPED / 'ATS CHECK PASS' or 'ATS CHECK FAIL' (exit 3).
"""
import argparse, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvgen

TRUE_SKILLS = cvgen.DATA.get('true_skills', [])


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s.replace('_', ' ')).strip()


def match(kw):
    k = norm(kw)
    for sk in TRUE_SKILLS:
        if k == norm(sk['canon']) or k in [norm(x) for x in sk.get('synonyms', [])]:
            return sk
    return None


def location_line(city, country, lang):
    """He/she really lives in cvgen.CITY: never claim to live elsewhere, only 'open to relocation'."""
    c = re.sub(r'[<>&|]', ' ', city).strip()[:40]
    k = re.sub(r'[<>&|]', ' ', country).strip()[:40]
    home = cvgen.CITY.lower()
    if not c or c.lower() == home or c.lower().startswith(home):
        return cvgen.HOME
    if c.lower() in ('remote', 'remote europe', 'remote eu', 'hybrid') or c.lower().startswith('remote'):
        return cvgen.HOME + (' (open to remote work)' if lang == 'EN' else ' (télétravail possible)')
    where = c + (', ' + k if k and k.lower() != c.lower() else '')
    return cvgen.HOME + (f' (open to relocation to {where})' if lang == 'EN' else f' (mobile pour une installation à {where})')
    # The CV never mentions sponsorship or a visa type (ATS keyword filters reject on it): work authorization is answered
    # truthfully in the application form questions only.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', required=True, choices=sorted(cvgen.FAM))
    ap.add_argument('--lang', required=True, choices=cvgen.LANGS)
    ap.add_argument('--role', required=True)
    ap.add_argument('--company', required=True)
    ap.add_argument('--city', required=True, help='city of the posting, e.g. Paris, Dublin, Berlin, Remote')
    ap.add_argument('--country', required=True, help='country of the posting, e.g. France, Ireland')
    ap.add_argument('--keywords', required=True, help='comma-separated keywords copied from the posting')
    a = ap.parse_args()

    kept, dropped, seen = [], [], set()
    for kw in [x.strip() for x in a.keywords.split(',') if x.strip()]:
        m = match(kw)
        if not m:
            dropped.append(kw); continue
        if m['canon'] in seen:
            continue
        seen.add(m['canon']); kept.append(m)
    if not kept:  # still build a per-offer CV (title + location + company); never fall back to the base CV
        print('NOTE no keyword of this posting is among your real facts; the CV still carries the posting title and location. DROPPED', dropped)

    role = re.sub(r'[<>&]', ' ', a.role).strip()[:90]
    company = re.sub(r'[<>&]', ' ', a.company).strip()[:50]
    term = lambda m: m.get(a.lang) or m['EN']
    terms = ', '.join(term(m) for m in kept[:10])
    if a.lang == 'FR':
        kw_line = ('En lien avec ce poste : ' + terms) if kept else None
        apply_line = f'Candidature au poste de {role} chez {company}.'
    else:
        kw_line = ('Matching this role: ' + terms) if kept else None
        apply_line = f'Applying for the {role} position at {company}.'

    loc = location_line(a.city, a.country, a.lang)
    contact = loc + ' | ' + cvgen.PHONE_MAIL
    out = os.path.join(cvgen.OUT, 'tailored', f'{cvgen.FILE_PREFIX}{cvgen.safe(company)}_{cvgen.safe(role)}_{a.lang}.pdf')
    path, size = cvgen.build(a.family, a.lang, out=out, apply_line=apply_line, kw_line=kw_line, contact=contact)
    import ats_check
    res = ats_check.check(path)
    print('CV', path)
    print('LOCATION LINE', loc)
    print('KEPT', [term(m) for m in kept])
    print('DROPPED (not in your real facts, never added):', dropped)
    if res['fails']:
        print('ATS CHECK FAIL', res['fails'], '-> do NOT upload this file')
        return 3
    print('ATS CHECK PASS', '(warnings: %s)' % res['warns'] if res['warns'] else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
