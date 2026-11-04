# Runner: nonstop application agents

```bash
python3 setup.py                               # asks who you are and WHAT YOU ARE LOOKING FOR (roles, level,
                                               # what to avoid, places, authorization); writes profile.json + config.json (git-ignored)
                                               # (or by hand: cp ../profile.example.json ../profile.json; cp config.example.json config.json)
cp ../boards.json boards.json                  # optional local copy
./run_all.sh                                   # watcher + supervisor + caffeinate
touch STOP                                     # stops the supervisor
```

- `supervisor.py`: keeps `MAXPAR` Claude-in-Chrome agents running (default 4), builds each prompt from
  `prompt_template.md` + `rules/` + a **duplicate ledger** (`applied.txt` plus every `CONFIRMED <company> | <role>` line found in `live.log`)
  + the priority queue + a rotating focus (`focus.example.json`). Agents run on Sonnet (`AGENT_MODEL` to change).
- `watcher.py`: polls Ashby / Greenhouse / Lever boards and queues only NEW matching postings (freshness).
- `livefilter.py`: turns the agent stream into a readable `live.log` (owner-only files, typed form values are never logged; set `AGENT_DEBUG=1` to also keep the raw transcript) that the ledger parses.
- Detects the 5-hour plan limit (agents dying within minutes) and sleeps 20 min.
- **Keep this folder outside `/tmp`**: macOS wipes `/tmp` on reboot, which kills a long run.
- Closed lid: `sudo pmset -a disablesleep 1` (undo with `0`). Everything else is your own browser session.
