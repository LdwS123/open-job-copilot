# Cloudflare Worker: 24/7 job watcher (free plan)

Scans 12 boards per minute (cron `* * * * *`), remembers what it has seen in KV, and queues
**new** postings that pass the tier filter in `src/index.js` (`INC` / `EXC` / `EUR` / `NAM` regexes).
A full cycle over ~300 boards takes ~25 minutes. Free-plan friendly: 12 boards x 1 fetch stays
under the 50-subrequest limit.

```bash
cd worker
npx wrangler kv namespace create STATE        # paste the id into wrangler.jsonc
npx wrangler secret put TOKEN                 # any long random string
npx wrangler deploy
curl "https://job-watcher.<your-subdomain>.workers.dev/queue?token=<TOKEN>&since=0"
```

- `GET /queue?token=...&since=<ms>`: matches found after `since`.
- `GET /run?token=...`: run one shard now (debugging).
- The first sight of a board is seeded silently, so you only get postings published *after* that.

Edit the regexes to your own target roles/locations. Keep `TOKEN` secret; never commit `.dev.vars`.
