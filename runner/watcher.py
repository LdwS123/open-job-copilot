#!/usr/bin/env python3
"""Local watcher: polls public ATS APIs (Ashby, Greenhouse, Lever) for the boards in ../boards.json
and appends NEW matching postings to queue.json. No credentials. Edit config.json to taste.

    cp config.example.json config.json && python3 watcher.py
"""
import json, re, time, os, urllib.request, urllib.parse, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue.json")
CFG = json.load(open(os.path.join(HERE, "config.json")))
BOARDS = json.load(open(os.path.join(HERE, "..", "boards.json")))
rx = lambda k: re.compile(CFG[k], re.I)
INC, EXC, BAD, T1, T2 = rx("include"), rx("exclude"), rx("bad_locations"), rx("tier1_locations"), rx("tier2_locations")
UA = {"User-Agent": "open-job-copilot/0.1"}

URL = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
}

ALLOWED_HOSTS = {"jobs.ashbyhq.com", "boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io",
                 "jobs.lever.co", "jobs.eu.lever.co"}

def safe_url(u):
    """Posting data comes from third parties: accept only https URLs on the ATS' own domains."""
    try:
        p = urllib.parse.urlparse(u or "")
    except Exception:
        return None
    return u if p.scheme == "https" and p.hostname in ALLOWED_HOSTS and not p.username else None

def get(u):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
    except Exception:
        return None

def jobs_of(b):
    ats, slug = b["ats"], b["slug"]
    d = get(URL[ats].format(slug))
    if ats == "ashby":
        return [(slug, ats, j.get("title", ""), j.get("location") or "", j.get("jobUrl") or j.get("applyUrl")) for j in (d or {}).get("jobs", [])]
    if ats == "greenhouse":
        # absolute_url may point at a company-controlled domain: rebuild the canonical Greenhouse URL from the job id
        return [(slug, ats, j.get("title", ""), (j.get("location") or {}).get("name", ""), f"https://boards.greenhouse.io/{slug}/jobs/{j['id']}")
                for j in (d or {}).get("jobs", []) if j.get("id")]
    return [(slug, ats, j.get("text", ""), (j.get("categories") or {}).get("location", ""), j.get("hostedUrl")) for j in (d if isinstance(d, list) else [])]

def tier(title, loc):
    if not INC.search(title) or EXC.search(title) or BAD.search(loc or ""):
        return 0
    return 1 if T1.search(loc or "") else 2 if T2.search(loc or "") else 0

def load():
    try:
        return json.load(open(QUEUE))
    except Exception:
        return {"seen": {}, "items": []}

def run_once():
    st = load()
    first = not st["seen"]  # first run only seeds, so you are not flooded with old postings
    new = 0
    with cf.ThreadPoolExecutor(8) as ex:
        for res in ex.map(jobs_of, BOARDS):
            for slug, ats, title, loc, url in res:
                url = safe_url(url)
                if not url or url in st["seen"]:
                    continue
                st["seen"][url] = int(time.time())
                t = tier(title, loc)
                if t and not first:
                    st["items"].append({"company": slug, "ats": ats, "title": title, "location": loc, "url": url,
                                        "tier": t, "found": int(time.time()), "dispatched": False})
                    new += 1
    json.dump(st, open(QUEUE, "w"))
    return new, len(st["seen"])

if __name__ == "__main__":
    while True:
        n, total = run_once()
        print(time.strftime("%H:%M:%S"), f"new_matches={n} total_seen={total}", flush=True)
        time.sleep(CFG.get("poll_seconds", 300))
