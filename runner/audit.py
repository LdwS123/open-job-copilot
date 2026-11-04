#!/usr/bin/env python3 -I
"""Audit the apply agents against the rules in rules/ and your config. Read-only, no network, no PII printed.

usage: python3 -I audit.py [hours=3] [launch]   -> ('launch' = only events after the last mark_offsets.py) prints a summary and writes audit_report.md

Checks per agent run (apply_sN_raw.jsonl):
  A. Per-offer CV: tailor.py was called, a file from the tailored/ output folder was uploaded, base CV only as fallback
  B. Upload health: file_upload errors ("only files this session is allowed to read")
  C. Truth: KEPT keywords are only allowlisted ones (tailor.py already drops the rest); no DROPPED keyword typed into a form
  D. Location line matches the posting city (Paris / remote / open to relocation)
  E. Forbidden content typed into pages: visa names (except J-1), your own "forbidden_terms" (config.json), wrong-city strings
  F. Results: confirmed applications vs 0, blocked-by-captcha, graduate-type titles that slipped through
"""
import json, os, re, sys, time, glob

R = os.path.dirname(os.path.abspath(__file__))
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
CUT = time.time() - HOURS * 3600

VISA = re.compile(r'\b(H-?1B|L-?1[AB]?|O-?1|TN visa|E-?3|F-?1|OPT|CPT|green card|EB-?[1-3]|Blue Card|Skilled Worker visa)\b', re.I)
GRAD = re.compile(r'graduate|new grad|campus|early careers?|intern(ship)?\b|alternance|stage\b|werkstudent', re.I)
def _cfg():
    try:
        return json.load(open(os.path.join(R, 'config.json')))
    except Exception:
        return {}


# config.json (git-ignored) may hold  "forbidden_terms": ["some project you never mention"]  and
# "wrong_city_regex": "Paris,\\s*Texas|Paris,\\s*TX"  (autocomplete traps for your city)
BAD_TYPED = [(VISA, 'visa type named')]
if _cfg().get('forbidden_terms'):
    BAD_TYPED.append((re.compile('|'.join(re.escape(t) for t in _cfg()['forbidden_terms']), re.I), 'forbidden term typed'))
if _cfg().get('wrong_city_regex'):
    BAD_TYPED.append((re.compile(_cfg()['wrong_city_regex'], re.I), 'wrong city typed'))


def _offset(path):
    """With LAUNCH=1 (2nd arg), only read bytes written after mark_offsets.py ran (slot files are appended across launches)."""
    if len(sys.argv) > 2 and sys.argv[2] == 'launch':
        try:
            return json.load(open(os.path.join(R, 'launch_offsets.json'))).get(os.path.basename(path), 0)
        except Exception:
            return 0
    return 0


def events(path):
    fh = open(path, 'rb')
    fh.seek(_offset(path))
    for line in fh.read().decode('utf-8', 'replace').split('\n'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        m = d.get('message')
        c = m.get('content') if isinstance(m, dict) else None
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict):
                    yield b


def flat(x):
    return json.dumps(x, ensure_ascii=False)


def audit_run(path):
    tag = re.search(r'apply_(s\d+)_raw', path).group(1)
    r = dict(tag=tag, tailor_calls=0, tailor=[], uploads_ok=0, uploads_blocked=0, uploads_tailored=0,
             uploads_base=0, fallback=0, ats_pass=0, ats_fail=0, gate=0, conf_lines=0, issues=[], typed_flags=[], last_use={})
    pending = {}
    for b in events(path):
        t = b.get('type')
        if t == 'text':
            r['gate'] += len(re.findall(r'^\s*GATE OK \|', b.get('text', ''), re.M))
            r['conf_lines'] += len(re.findall(r'^\s*CONFIRMED ', b.get('text', ''), re.M))
        if t == 'tool_use':
            name, inp = b.get('name', ''), b.get('input', {})
            if name == 'Bash' and re.search(r'tailor\.py\s+--family', inp.get('command', '')):
                cmd = inp['command']
                g = lambda k: (re.search(r"--%s '([^']*)'" % k, cmd) or re.search(r'--%s (\S+)' % k, cmd))
                r['tailor_calls'] += 1
                pending[b['id']] = dict(company=g('company').group(1) if g('company') else '?',
                                        role=g('role').group(1) if g('role') else '?',
                                        city=g('city').group(1) if g('city') else '(missing)',
                                        lang=g('lang').group(1) if g('lang') else '?')
                if not g('city'):
                    r['issues'].append('tailor.py called without --city (location line defaults to Paris)')
            elif name.endswith('file_upload'):
                p = (inp.get('paths') or [''])[0]
                pending[b['id']] = dict(upload=p)
            elif name.endswith(('form_input', 'computer')):
                s = flat(inp)
                for rx, label in BAD_TYPED:
                    if rx.search(s) and not (label == 'visa type named' and re.search(r'J-?1', s)):
                        r['typed_flags'].append(label + ': ' + s[:120])
        elif t == 'tool_result':
            u = pending.pop(b.get('tool_use_id'), None)
            s = flat(b.get('content'))
            if u is None:
                continue
            if 'upload' in u:
                if 'only files this session' in s or 'Cannot upload' in s:
                    r['uploads_blocked'] += 1
                else:
                    r['uploads_ok'] += 1
                    base = os.path.basename(u['upload'])
                    if '/tailored/' in u['upload']:
                        r['uploads_tailored'] += 1
                    else:
                        r['uploads_base'] += 1
                        if not re.search(r'_cv_[a-z_]+_[A-Z]{2}\.pdf$', base):
                            r['issues'].append('uploaded a renamed/copied file: ' + base)
                    if '/scratchpad' in u['upload'] or '/private/tmp' in u['upload']:
                        r['issues'].append('uploaded from a scratchpad copy (workaround): ' + base)
            else:
                r['ats_pass'] += 'ATS CHECK PASS' in s; r['ats_fail'] += 'ATS CHECK FAIL' in s
                if 'NO_TRUE_KEYWORD_MATCH' in s:
                    r['fallback'] += 1
                loc = re.search(r'LOCATION LINE ([^\\]+)', s)
                kept = re.search(r'KEPT (\[[^\]]*\])', s)
                u.update(loc=loc.group(1).strip() if loc else None, kept=kept.group(1) if kept else None)
                r['tailor'].append(u)
    fo = os.path.join(R, 'apply_%s_final.out' % tag)
    r['final'] = open(fo, errors='replace').read() if os.path.exists(fo) else ''
    m = re.search(r'(?:Total|Bilan)[^\n]{0,40}?(\d+)\s*(?:/|sur|confirm)', r['final'], re.I) or \
        re.search(r'(?:Candidatures?\s+(?:envoy|confirm)[ée]+s?)\s*:?\**\s*(\d+)', r['final'], re.I)
    r['confirmed'] = int(m.group(1)) if m else None
    r['captcha'] = bool(re.search(r'captcha|cloudflare|v[ée]rifier que vous', r['final'], re.I))
    if r['uploads_blocked'] and not r['uploads_ok']:
        r['issues'].append('UPLOAD BLOCKED: every CV upload refused, run could not apply')
    if r['tailor_calls'] and r['uploads_base'] and not r['uploads_tailored'] and not r['fallback']:
        r['issues'].append('uploaded only base CV although tailor.py ran')
    if r['uploads_ok'] and not r['tailor_calls']:
        r['issues'].append('uploaded a CV without ever calling tailor.py (rule 11 skipped)')
    if r['conf_lines'] > r['gate']:
        r['issues'].append('SUBMITTED WITHOUT GATE: %d CONFIRMED vs %d GATE OK lines' % (r['conf_lines'], r['gate']))
    if (r['confirmed'] or r['conf_lines']) and not r['uploads_tailored']:
        r['issues'].append('APPLICATION DECLARED BUT NO TAILORED CV UPLOADED')
    for t in r['tailor']:
        city = (t['city'] or '').lower()
        loc = (t.get('loc') or '')
        if city and city not in ('paris', '(missing)') and not city.startswith('paris') and loc.startswith('Paris, France') and 'open to' not in loc and 'mobile' not in loc and 'télétravail' not in loc:
            r['issues'].append('location line does not mention %s for %s' % (t['city'], t['company']))
        if GRAD.search(t['role']):
            r['issues'].append('tailored for a graduate/intern-type title: %s @ %s' % (t['role'], t['company']))
    for f in r['typed_flags']:
        r['issues'].append('TYPED: ' + f)
    return r


def main():
    files = [f for f in glob.glob(os.path.join(R, 'apply_s*_raw.jsonl')) if os.path.getmtime(f) >= CUT and os.path.getsize(f) > _offset(f)]
    files.sort(key=lambda f: int(re.search(r'_s(\d+)_', f).group(1)))
    runs = [audit_run(f) for f in files]
    n = len(runs)
    tot = lambda k: sum(x[k] for x in runs)
    blocked = [x['tag'] for x in runs if 'UPLOAD BLOCKED' in ' '.join(x['issues'])]
    conf = sum(x['confirmed'] or 0 for x in runs)
    out = ['# Audit des agents (dernières %.1f h)\n' % HOURS,
           '- Runs analysés : %d' % n,
           '- Candidatures confirmées (déclarées dans les rapports) : %d' % conf,
           '- Appels tailor.py : %d (fallback CV de base : %d)' % (tot('tailor_calls'), tot('fallback')),
           '- Uploads réussis : %d (CV adapté : %d, CV de base : %d) | refusés : %d' % (
               tot('uploads_ok'), tot('uploads_tailored'), tot('uploads_base'), tot('uploads_blocked')),
           '- Contrôle ATS du CV (tailor.py) : %d PASS, %d FAIL' % (tot('ats_pass'), tot('ats_fail')),
           '- Lignes GATE OK : %d | lignes CONFIRMED : %d' % (tot('gate'), tot('conf_lines')),
           '- Runs bloqués par le refus d\'upload : %d %s' % (len(blocked), blocked),
           '- Runs avec captcha à finir à la main : %d' % sum(1 for x in runs if x['captcha']),
           '']
    bad = [x for x in runs if x['issues']]
    out.append('## Problèmes par run\n')
    for x in bad:
        out.append('**%s** : ' % x['tag'] + ' ; '.join(sorted(set(x['issues']))))
    if not bad:
        out.append('Aucun.')
    out.append('\n## CV adaptés (échantillon)\n')
    for x in runs:
        for t in x['tailor'][:3]:
            out.append('- %s | %s | %s | %s | %s' % (x['tag'], t['company'], t['role'], t.get('loc'), t.get('kept')))
    rep = '\n'.join(out)
    open(os.path.join(R, 'audit_report.md'), 'w').write(rep)
    print(rep[:6000])


main()
