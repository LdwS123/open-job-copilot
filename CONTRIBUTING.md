# Contributing

Small, focused PRs are the easiest to merge.

**Most useful contributions**
- New company boards in `boards.json` (`{"ats": "ashby|greenhouse|lever", "slug": "..."}`); run `runner/discover_boards.py` to verify a slug first. Keep the list free of duplicates (CI checks).
- New ATS adapters (Workable, SmartRecruiters, Teamtailor...) in `mcp-server/lib.js` with a test in `mcp-server/test.js`.
- Better agent rules in `runner/rules/` (shorter and clearer beats longer).

**Ground rules**
- Only public endpoints. No scraping behind a login, no captcha solving, no account creation.
- The agent must stay truthful: never add a rule that fakes authorization, experience or documents.
- Never commit personal data. Before pushing: `git ls-files | xargs grep -lE "your-name|your-email"` should be empty.
- Anything that puts third-party text into an agent prompt must go through `runner/sanitize.py`.

**Checks**: `(cd mcp-server && npm test)` and `python3 -m unittest discover -s tests`.
