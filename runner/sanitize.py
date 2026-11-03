"""Untrusted-text defences shared by the supervisor and its tests.

Queue entries come from third-party job boards and the ledger from agent output, so both are treated as hostile
before they are placed in an agent prompt."""
import re, unicodedata, urllib.parse

ALLOWED_HOSTS = {"jobs.ashbyhq.com", "boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io",
                 "jobs.lever.co", "jobs.eu.lever.co", "apply.workable.com", "careers.smartrecruiters.com", "jobs.smartrecruiters.com"}

def clean(x, n=120):
    """Queue/ledger text comes from third-party pages or agent output. NFKC-normalise, keep letters, digits, marks, spaces and
    basic punctuation, neutralise delimiter characters."""
    t = unicodedata.normalize("NFKC", str(x))
    t = "".join(ch if (unicodedata.category(ch)[0] in "LNM" or ch == " " or ch in ".,;:!?'\"()[]&+-_/@#%") else " " for ch in t)
    return re.sub(r"\s+", " ", t).replace("|", "/").replace("<", "(").replace(">", ")").strip()[:n]

URL_RE = re.compile(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9._~%/?=&#:+-]*")

def ok_url(u):
    u = str(u)
    return bool(URL_RE.fullmatch(u)) and urllib.parse.urlparse(u).hostname in ALLOWED_HOSTS
