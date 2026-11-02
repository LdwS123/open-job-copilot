# open-job-copilot

**Free, open-source tooling to find jobs, and (optionally) apply to them with your own AI agent.**
No API keys. No scraping of login-walled sites. Everything reads the *public* careers APIs that
companies themselves publish (Ashby, Greenhouse, Lever), including many YC and a16z-backed startups.

| Part | What it does | Cost |
|---|---|---|
| [`mcp-server/`](mcp-server) | **MCP server**: ask Claude (or any MCP client) *"find me junior sales roles in Europe at YC startups"* and get live postings with apply links | free |
| [`worker/`](worker) | **Cloudflare Worker**: watches ~790 boards 24/7 and queues *new* postings the minute they appear (be first to apply) | free plan |
| [`runner/`](runner) | Local watcher + supervisor that feeds a queue to Claude-in-Chrome agents that fill forms **in your own logged-in browser** | your Claude plan |
| [`boards.json`](boards.json) | The curated board list (ats + slug). PRs welcome | n/a |

> Friends: start with [FRIENDS.md](FRIENDS.md) (5-minute setup with an onboarding agent).

## 1. Use the MCP server (2 minutes)

```bash
git clone https://github.com/LdwS123/open-job-copilot && cd open-job-copilot/mcp-server && npm install
claude mcp add job-copilot -- node "$(pwd)/index.js"
```

Claude Desktop / any client: add to the MCP config

```json
{ "mcpServers": { "job-copilot": { "command": "node", "args": ["/abs/path/open-job-copilot/mcp-server/index.js"] } } }
```

Tools: `search_jobs`, `get_company_jobs`, `discover_board`, `list_boards`.

Example prompts:
- *"Search jobs: keywords sales, exclude senior/director, location paris france europe emea."*
- *"Remote-only growth or community roles at the companies in your list, newest first."*
- *"Does the company `linear` have a public board? Which ATS?"*

## 2. Grow the company list (YC, a16z, anything)

```bash
echo "ramp linear posthog mercor" | python3 runner/discover_boards.py --write
```
Feed it slugs from [ycombinator.com/companies?isHiring=true](https://www.ycombinator.com/companies?isHiring=true)
or [a16z.com/portfolio](https://a16z.com/portfolio). It probes Ashby / Greenhouse / Lever and merges hits
into `boards.json` (then copy it to `mcp-server/` and regenerate `worker/src/boards.js`).

## 3. Be first: the 24/7 watcher

See [`worker/README.md`](worker/README.md): one `wrangler deploy` on Cloudflare's free plan.
Or run `runner/watcher.py` locally (`cp runner/config.example.json runner/config.json`).

## 4. Let an agent apply for you (optional, read the limits)

```bash
cp profile.example.json profile.json     # your real, truthful data (git-ignored)
cd runner && cp config.example.json config.json
python3 watcher.py &                      # fills queue.json with new postings
python3 supervisor.py                     # launches Claude-in-Chrome agents (needs `claude` CLI + Chrome extension)
```

**Guardrails baked into the prompt** ([`runner/prompt_template.md`](runner/prompt_template.md)): truth only,
your real work-authorization answers, no account creation, no captcha solving, no marketing opt-ins,
one application per company, only *confirmed* submissions are counted.

**Honest limits**
- Applying runs in *your* browser with *your* sessions. It is bounded by your AI plan's usage limits, not by CPU.
  More parallel agents burn quota faster, they don't multiply results.
- Many forms (captcha, account wall, custom widgets) can't be completed automatically; the agent skips and reports.
- Volume is not a strategy by itself. Tailor your profile, apply where you truly fit, answer recruiters fast.
- Posting titles, locations and URLs come from third-party boards and are treated as untrusted: URLs are restricted to the ATS hosts, queue text is sanitised and fenced, and the agent prompt forbids following instructions found in postings. For extra safety run the agents in a dedicated Chrome profile that has no other sensitive logins.
- Respect each site's terms and rate limits. This project only reads public JSON endpoints.

## Privacy
`profile.json`, `config.json`, `queue.json`, CVs and tokens are git-ignored. Don't commit personal data.

## License
MIT
