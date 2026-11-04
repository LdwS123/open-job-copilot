---
name: onboard
description: Interview a job seeker and create their truthful profile.json for open-job-copilot
---

Ask these in small groups (not all at once), in the user's language, then write `profile.json` using `profile.example.json` as the template:

1. Name, email, phone, city + country, LinkedIn / GitHub / portfolio.
2. Languages and level (honest).
3. **Where can you legally work without sponsorship? Where would you need sponsorship?** (put in `authorized_in` / `needs_sponsorship_in`)
4. **What are they looking for?** Ask it explicitly, never assume: target job titles (`target_roles`), level (`seniority`), titles/words to avoid (`avoid_roles`, e.g. graduate programmes, senior, intern), and any special programs they DO accept despite the avoid list (`special_programs`, e.g. trainee or exchange-visitor programs abroad). Also industries they like or want to avoid. Offer `python3 runner/setup.py` as the same questionnaire in the terminal; it also derives `runner/config.json`.
5. Locations: remote? willing to relocate where?
6. Salary expectation range and notice period (or "negotiable / immediately").
7. CV: absolute path to the PDF. If none, offer to draft a CV from the facts they give (facts only).
8. Three to five proof points: things they actually did, with numbers only if the numbers are real.
9. Whether required consent checkboxes (privacy policy / data processing) may be ticked for them: set `allow_required_consents` accordingly. Marketing opt-ins are never ticked.

Read the finished profile back to them and ask for corrections before saving. Never fill a field with a guess.
