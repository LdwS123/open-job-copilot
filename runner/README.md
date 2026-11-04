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

## One tailored, ATS-safe CV per application (works for anyone)

Most applicant tracking systems rank on the posting's own words and drop résumés that do not parse. This folder
generates a fresh one-page PDF for **every** posting from YOUR true facts, checks that an ATS can parse it, and
gates every submit on that check.

```bash
pip install -r requirements.txt                 # reportlab + pypdf
cp ../cv_data.example.json ../cv_data.json      # then replace EVERYTHING with your own true facts (git-ignored)
python3 -I cvgen.py                             # base CVs, one per family and language, in output_dir (default ~/job-copilot-cv)
python3 -I ats_check.py ~/job-copilot-cv        # parse check, writes ats_check_report.md, exit 1 on FAIL
python3 -I tailor.py --family sdr_bdr --lang EN --role 'Sales Development Representative' --company 'Acme' \
        --city 'Dublin' --country 'Ireland' --keywords 'outbound,HubSpot,cold calling'
```

- `cv_data.json`: your name, contacts, links, one block per language (`EN`, `FR`, ...), `families` (summary angle per kind of
  role) and `true_skills` (the ONLY keywords the tailor may ever add). Nothing outside it can appear in a CV.
- `cvgen.py`: single column, real selectable text (embedded Carlito/Lato, SIL OFL), clickable links, right-aligned dates,
  A4 or Letter (`page_size`), one-page fit loop. No tables, columns, images or text boxes.
- `tailor.py`: mirrors the posting's exact title and company in the summary, keeps only the posting keywords that are in
  `true_skills` (prints `KEPT` / `DROPPED`), writes the location line (home city, "open to remote work" or "open to
  relocation to <City>, <Country>"), saves under `output_dir/tailored/`, runs the ATS check and prints `ATS CHECK PASS|FAIL`.
- `ats_check.py`: reads the PDF like a parser: extractable text, name first, one e-mail and phone in the header, standard
  section headings in order, a parseable date on every entry, fonts and sizes, links. It is an approximation: nobody outside
  an ATS vendor can see inside the real parser, so a PASS lowers the risk, it does not guarantee a result.
- `rules/ats_tailoring.md` is injected into every agent prompt: tailor per offer, upload only after `ATS CHECK PASS`, and the
  **hard gate** (tailored file uploaded, no empty required field, then `GATE OK | ... ` before submit, `CONFIRMED ...` after).
- `audit.py [hours] [launch]`: read-only audit of the agent transcripts (tailor called? tailored file uploaded? gate lines?
  forbidden terms typed?). Optional `forbidden_terms` and `wrong_city_regex` in `config.json` extend the checks.
  `mark_offsets.py` (called by `run_all.sh`) marks where a launch starts, `stop_after.py N SECONDS` is a bounded test run.
- Keep `output_dir` on a path **without spaces** (browsers' file-upload tools may refuse some folders).
- The same pipeline serves several people: one `cv_data.json` (or `JOB_CV_DATA=/path/to/other.json`) per person.
