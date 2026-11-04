#!/usr/bin/env python3
"""First-run questionnaire: asks WHO you are and WHAT you are looking for, then writes
../profile.json and config.json (both git-ignored). Re-run any time:  python3 setup.py

Nothing is sent anywhere; answers stay in these two local files. Press Enter to keep the [default].
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, '..', 'profile.json')
CONFIG = os.path.join(HERE, 'config.json')


def load(path):
    try: return json.load(open(path))
    except Exception: return {}


def ask(q, default='', hint=''):
    d = f' [{default}]' if default else ''
    h = f'  ({hint})' if hint else ''
    a = input(f'{q}{h}{d}: ').strip()
    return a or default


def items(s):
    return [x.strip() for x in re.split(r'[,;\n]', s) if x.strip()]


def rx(words):  # list of plain words -> case-insensitive regex alternation
    return '|'.join(re.escape(w.lower()) for w in words)


def yes(q, default=True):
    a = input(f'{q} [{"Y/n" if default else "y/N"}]: ').strip().lower()
    return default if not a else a.startswith('y')


def main():
    p, c = load(PROFILE), load(CONFIG)
    print('\n=== 1/4  Who are you? (used to fill forms, never invented) ===')
    p['full_name'] = ask('Full name', p.get('full_name', ''))
    p['email'] = ask('Email', p.get('email', ''))
    p['phone'] = ask('Phone', p.get('phone', ''))
    p['city'] = ask('City you really live in', p.get('city', ''))
    p['country'] = ask('Country', p.get('country', ''))
    p['linkedin'] = ask('LinkedIn URL', p.get('linkedin', ''))
    p['github'] = ask('GitHub / portfolio URL (optional)', p.get('github', ''))
    p['cv_path'] = ask('Absolute path to your CV PDF', p.get('cv_path', ''))
    p['one_paragraph_truthful_story'] = ask('2-3 TRUE sentences: what you did, what you want next',
                                            p.get('one_paragraph_truthful_story', ''))

    print('\n=== 2/4  What are you looking for? ===')
    roles = items(ask('Job titles you want', ', '.join(p.get('target_roles_list', [])) or 'SDR, business developer, customer success',
                      'comma-separated, e.g. product manager, content creator, growth, account executive'))
    seniority = ask('Your level', p.get('seniority', 'junior'), 'junior / mid / senior')
    avoid = items(ask('Titles or words to AVOID', ', '.join(p.get('avoid_list', [])) or 'senior, head of, director, graduate programme',
                      'e.g. graduate, intern, engineer, legal'))
    p['target_roles'] = ', '.join(roles)
    p['target_roles_list'], p['avoid_list'], p['seniority'] = roles, avoid, seniority
    p['avoid_roles'] = ', '.join(avoid)
    special = ask('Special programs you ACCEPT even if they look like "avoid" (optional)', p.get('special_programs', ''),
                  'e.g. "US trainee / exchange-visitor programs at startups"')
    p['special_programs'] = special or 'none'

    print('\n=== 3/4  Where? Work authorization (answered truthfully on every form) ===')
    prefer = items(ask('Preferred places (cities/countries/regions, "remote" ok)', ', '.join(p.get('preferred_locations', [])) or 'Paris, France, Europe, remote',
                       'comma-separated'))
    other = items(ask('Other places you would consider ONLY if the employer can sponsor / special program', ', '.join(p.get('other_locations', [])),
                      'e.g. United States, Canada'))
    p['preferred_locations'], p['other_locations'] = ', '.join(prefer), ', '.join(other) or 'none'
    p['authorized_in'] = items(ask('Where are you legally allowed to work with NO sponsorship', ', '.join(p.get('authorized_in', [])) or 'EU/EEA',
                                   'comma-separated'))
    p['needs_sponsorship_in'] = items(ask('Where would you NEED sponsorship', ', '.join(p.get('needs_sponsorship_in', [])) or 'United States, Canada, United Kingdom'))
    p['relocation'] = 'yes' if yes('Are you willing to relocate for a role in a place where you are authorized?', p.get('relocation', 'yes') == 'yes') else 'no'

    print('\n=== 4/4  Defaults ===')
    p['default_salary_answer'] = ask('Salary answer when free text', p.get('default_salary_answer', 'Negotiable / open to discuss'))
    p['default_notice_answer'] = ask('Notice period answer', p.get('default_notice_answer', 'Available immediately'))
    p['allow_required_consents'] = yes('Tick REQUIRED privacy/data-processing boxes (never marketing opt-ins)?', p.get('allow_required_consents', True))
    p['report_language'] = ask('Language for reports', p.get('report_language', 'English'))

    # derive the watcher config from the answers
    c.setdefault('bad_locations', 'japan|india|singapore|australia|brazil|korea|china')
    c['include'] = rx(roles) or 'a^'
    c['exclude'] = rx(avoid) or 'a^'
    c['tier1_locations'] = rx(prefer) or 'remote'
    c['tier2_locations'] = rx(other) or 'a^'
    c.setdefault('poll_seconds', 300)

    json.dump(p, open(PROFILE, 'w'), indent=2, ensure_ascii=False)
    json.dump(c, open(CONFIG, 'w'), indent=2, ensure_ascii=False)
    os.chmod(PROFILE, 0o600)
    print(f'\nSaved {os.path.abspath(PROFILE)} and {CONFIG}. Both are git-ignored. Edit them or re-run setup.py any time.')


if __name__ == '__main__':
    main()
