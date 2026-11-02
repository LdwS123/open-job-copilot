#!/usr/bin/env python3
"""Keeps N Claude-in-Chrome agents applying in a loop. Needs the `claude` CLI with the Chrome extension.

    python3 supervisor.py            # touch STOP to stop it

Honest limit: throughput is bounded by your Claude plan's usage limits and by how fast forms can be
filled in your own browser. More parallel agents just burn quota faster.
"""
import json, os, subprocess, time, re

HERE = os.path.dirname(os.path.abspath(__file__))
MAXPAR = int(os.environ.get("MAXPAR", "3"))
PROFILE = json.load(open(os.path.join(HERE, "..", "profile.json")))
TEMPLATE = open(os.path.join(HERE, "prompt_template.md")).read()
QUEUE = os.path.join(HERE, "queue.json")
LEDGER = os.path.join(HERE, "applied.txt")  # one company per line, append after each confirmed application

def fill(t):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(PROFILE.get(m.group(1), m.group(0))), t)

def applied():
    try:
        return sorted({l.strip() for l in open(LEDGER) if l.strip()})
    except Exception:
        return []

def pop_queue(n=20):
    try:
        d = json.load(open(QUEUE))
    except Exception:
        return []
    done = {a.lower() for a in applied()}
    pick, seen = [], set()
    for x in sorted((x for x in d["items"] if not x["dispatched"]), key=lambda x: (x["tier"], -x["found"])):
        c = x["company"].lower()
        if c in done or c in seen:
            continue
        pick.append(x); seen.add(c)
        if len(pick) >= n:
            break
    keys = {x["url"] for x in pick}
    for x in d["items"]:
        if x["url"] in keys:
            x["dispatched"] = True
    json.dump(d, open(QUEUE, "w"))
    return pick

def running():
    return int(subprocess.run('pgrep -f "^claude --chrome" | wc -l', shell=True, capture_output=True, text=True).stdout.strip() or 0)

i = 0
while not os.path.exists(os.path.join(HERE, "STOP")):
    if running() >= MAXPAR:
        time.sleep(30); continue
    q = "\n".join(f"- {x['company']} | {x['title']} | {x['location']} | {x['url']}" for x in pop_queue())
    prompt = (fill(TEMPLATE) + "\n\nALREADY APPLIED (never again): " + ", ".join(applied())
              + "\n\nPRIORITY QUEUE:\n" + (q or "(empty, use the FOCUS sources: a16z / YC portfolios, ATS boards)"))
    pf = os.path.join(HERE, f"prompt_{i}.txt")
    open(pf, "w").write(prompt)
    subprocess.Popen(["claude", "--chrome", "-p", prompt, "--allowedTools", "mcp__claude-in-chrome__*"],
                     stdout=open(os.path.join(HERE, f"agent_{i}.out"), "w"), stderr=subprocess.STDOUT)
    i += 1
    time.sleep(60)
