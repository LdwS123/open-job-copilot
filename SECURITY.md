# Security policy

The runner feeds third-party text (job titles, locations, URLs) to an AI agent that controls a real browser, so
prompt injection is the main threat. Defences: strict URL allowlist, character allowlist, fenced untrusted blocks,
owner-only logs (see `runner/sanitize.py` and the README security model).

**Report a vulnerability** privately through GitHub's *Security > Report a vulnerability* on this repository. Please
don't open a public issue for anything that could be used against users. I aim to respond within a few days.

**Hardening tips for users**: run agents in a dedicated Chrome profile, keep `profile.json` out of version control,
and never put credentials into prompts or rules.
