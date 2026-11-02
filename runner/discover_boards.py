#!/usr/bin/env python3
"""Find which public ATS board (Ashby / Greenhouse / Lever) hosts each company slug and merge hits into ../boards.json.

    echo "ramp linear posthog" | python3 discover_boards.py          # dry run
    echo "ramp linear posthog" | python3 discover_boards.py --write  # merge into boards.json

Feed it slugs from the YC directory (ycombinator.com/companies?isHiring=true) or a16z.com/portfolio.
"""
import json, os, sys, urllib.request, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); BJ = os.path.join(HERE, "..", "boards.json")
URL = {"ashby": "https://api.ashbyhq.com/posting-api/job-board/{}", "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs", "lever": "https://api.lever.co/v0/postings/{}?mode=json"}
def probe(a):
    ats, slug = a
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(URL[ats].format(slug), headers={"User-Agent": "open-job-copilot/0.1"}), timeout=15))
        n = len(d) if isinstance(d, list) else len(d.get("jobs", []))
        return (ats, slug, n)
    except Exception:
        return (ats, slug, 0)
slugs = sorted({s.strip().lower() for s in sys.stdin.read().split() if s.strip()})
have = {(b["ats"], b["slug"]) for b in json.load(open(BJ))}
todo = [(a, s) for s in slugs for a in URL if (a, s) not in have]
with cf.ThreadPoolExecutor(10) as ex:
    hits = [r for r in ex.map(probe, todo) if r[2] > 0]
for ats, slug, n in hits: print(f"{ats:11} {slug:28} {n} open roles")
if "--write" in sys.argv and hits:
    b = json.load(open(BJ)); b += [{"ats": a, "slug": s} for a, s, _ in hits]
    json.dump(sorted(b, key=lambda x: (x["ats"], x["slug"])), open(BJ, "w"), indent=0)
    print(f"merged {len(hits)} boards (remember to copy boards.json to mcp-server/ and regenerate worker/src/boards.js)")
