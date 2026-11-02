# Job hunting with a friend-sized copilot (5 minutes)

You need: Node 18+, [Claude Code](https://claude.com/claude-code), Chrome with the Claude-in-Chrome extension (only for auto-apply).

```bash
git clone https://github.com/LdwS123/open-job-copilot && cd open-job-copilot
(cd mcp-server && npm install)
claude mcp add job-copilot -- node "$(pwd)/mcp-server/index.js"
claude            # then type:  /onboard   and afterwards:  use the job-copilot agent to find me roles
```

What happens:
1. `/onboard` asks you questions and writes `profile.json` (stays on your machine, git-ignored).
2. The agent searches ~1,100 startup / YC / a16z / big-tech boards live and shows a shortlist.
3. It drafts honest answers; you approve; it fills forms **in your own Chrome**, one at a time.
4. After a week it shows applications sent vs replies, so you learn what actually works.

It will never invent experience, answer work-authorization questions untruthfully, create accounts, or solve captchas.
It uses *your* Claude plan and *your* browser, so nothing is shared with the repo owner.
