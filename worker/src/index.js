import { BOARDS } from "./boards.js";

const SHARD = 12; // boards per cron run (free plan: 50 subrequests, 10ms CPU)
const INC = /\b(sdr|bdr|adr|business develop|sales develop|account (executive|manager|development)|customer success|customer support specialist|growth|partnership|partner manager|community|creator|influencer|content|social media|chief of staff|founder'?s? associate|go-to-market|gtm|revenue operations|sales operations|solutions? (engineer|consultant)|implementation|onboarding|commercial|chargé|business dev|outbound|inside sales|sales representative|sales associate|account coordinator)\b/i;
const EXC = /\b(senior|sr\.?|head of|director|vp|vice president|principal|staff|lead|manager,? (enterprise|strategic)|intern|stage|alternance|apprenti|werkstudent|developer|designer|scientist|recruiter|counsel|legal|finance|accountant|payroll)\b|\bengineer\b(?! ?sales)/i;
const BADLOC = /japan|tokyo|india|bangalore|singapore|australia|sydney|brazil|mexico|korea|china|dubai|uae|israel|tel aviv|philippines|indonesia|new zealand|south africa|latam|apac/i;
const EUR = /paris|france|emea|europe|dublin|ireland|london|\buk\b|united kingdom|amsterdam|netherlands|berlin|germany|deutschland|munich|hamburg|frankfurt|cologne|madrid|spain|barcelona|lisbon|portugal|brussels|belgium|milan|italy|rome|zurich|switzerland|geneva|stockholm|sweden|gothenburg|malm|copenhagen|denmark|oslo|norway|helsinki|finland|vienna|austria|prague|czech|warsaw|poland|krakow|budapest|bucharest|athens|tallinn|riga|vilnius|luxembourg|remote|anywhere|worldwide/i;
const NAM = /united states|u\.s\.|\busa?\b|canada|new york|san francisco|austin|boston|seattle|chicago|los angeles|toronto|remote/i;
const SENIOR_AE = /(account executive|enterprise|strategic|mid[- ]market|sled|government|expert|principal|architect|specialist, gtm|\bcsm\b|renewals)/i;
const JUNIOR = /(associate|junior|graduate|entry|early career|new grad|trainee|sdr|bdr|adr|business development rep|sales development|development rep|coordinator|assistant)/i;

function tier(title, loc) {
  if (!INC.test(title) || EXC.test(title)) return 0;
  if (BADLOC.test(loc || "")) return 0;
  if (SENIOR_AE.test(title) && !JUNIOR.test(title)) return 0;
  if (EUR.test(loc || "")) return 1;
  if (NAM.test(loc || "")) return 2;
  return 0;
}

async function fetchBoard(ats, slug) {
  const urls = {
    ashby: `https://api.ashbyhq.com/posting-api/job-board/${slug}`,
    greenhouse: `https://boards-api.greenhouse.io/v1/boards/${slug}/jobs`,
    lever: `https://api.lever.co/v0/postings/${slug}?mode=json`,
  };
  const r = await fetch(urls[ats], { headers: { "User-Agent": "Mozilla/5.0" } });
  if (!r.ok) return [];
  const d = await r.json();
  if (ats === "ashby") return (d.jobs || []).map(j => ({ title: j.title || "", loc: j.location || "", url: j.jobUrl || j.applyUrl }));
  if (ats === "greenhouse") return (d.jobs || []).map(j => ({ title: j.title || "", loc: (j.location || {}).name || "", url: j.absolute_url }));
  return (Array.isArray(d) ? d : []).map(j => ({ title: j.text || "", loc: (j.categories || {}).location || "", url: j.hostedUrl }));
}

async function scanShard(env) {
  const minute = Math.floor(Date.now() / 60000);
  const nShards = Math.ceil(BOARDS.length / SHARD);
  const idx = minute % nShards;
  const boards = BOARDS.slice(idx * SHARD, idx * SHARD + SHARD);
  const found = [];
  await Promise.all(boards.map(async ([ats, slug]) => {
    try {
      const jobs = await fetchBoard(ats, slug);
      const key = `seen:${ats}:${slug}`;
      const prev = await env.STATE.get(key, "json");
      const seen = new Set(prev || []);
      const fresh = jobs.filter(j => j.url && !seen.has(j.url));
      if (!fresh.length) return;
      if (prev) { // first sight of a board is seeded silently
        for (const j of fresh) {
          const t = tier(j.title, j.loc);
          if (t) found.push({ company: slug, ats, title: j.title, location: j.loc, url: j.url, tier: t, found: Date.now() });
        }
      }
      await env.STATE.put(key, JSON.stringify(jobs.map(j => j.url).filter(Boolean)));
    } catch (e) { console.log("board error", ats, slug, String(e)); }
  }));
  if (found.length) {
    const q = (await env.STATE.get("queue", "json")) || [];
    const merged = found.concat(q).slice(0, 600);
    await env.STATE.put("queue", JSON.stringify(merged));
  }
  console.log(`shard ${idx}/${nShards} boards=${boards.length} new_matches=${found.length}`);
}

export default {
  async scheduled(event, env, ctx) { ctx.waitUntil(scanShard(env)); },
  async fetch(req, env) {
    const u = new URL(req.url);
    if (u.pathname === "/run" && u.searchParams.get("token") === env.TOKEN) { await scanShard(env); return new Response("ran"); }
    if (u.pathname !== "/queue" || u.searchParams.get("token") !== env.TOKEN) return new Response("not found", { status: 404 });
    const since = Number(u.searchParams.get("since") || 0);
    const q = (await env.STATE.get("queue", "json")) || [];
    return Response.json(q.filter(x => x.found > since));
  },
};
