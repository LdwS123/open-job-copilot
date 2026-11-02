// Core logic: fetch public ATS job boards and normalise them. No credentials needed.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
export const BOARDS = JSON.parse(readFileSync(join(here, "boards.json"), "utf8"));

const UA = { "User-Agent": "open-job-copilot/0.1 (+https://github.com/LdwS123/open-job-copilot)" };

const ENDPOINTS = {
  ashby: (s) => `https://api.ashbyhq.com/posting-api/job-board/${encodeURIComponent(s)}`,
  greenhouse: (s) => `https://boards-api.greenhouse.io/v1/boards/${encodeURIComponent(s)}/jobs`,
  lever: (s) => `https://api.lever.co/v0/postings/${encodeURIComponent(s)}?mode=json`,
};

export const SUPPORTED_ATS = Object.keys(ENDPOINTS);

export function normalise(ats, slug, d) {
  if (ats === "ashby")
    return (d?.jobs || []).map((j) => ({
      company: slug, ats, title: j.title || "", location: j.location || "",
      remote: !!j.isRemote || /remote/i.test(j.location || ""),
      url: j.jobUrl || j.applyUrl, published: j.publishedAt || null,
      department: j.department || j.team || null,
    }));
  if (ats === "greenhouse")
    return (d?.jobs || []).map((j) => ({
      company: slug, ats, title: j.title || "", location: j.location?.name || "",
      remote: /remote/i.test(j.location?.name || ""),
      url: j.absolute_url, published: j.updated_at || null, department: null,
    }));
  return (Array.isArray(d) ? d : []).map((j) => ({
    company: slug, ats, title: j.text || "", location: j.categories?.location || "",
    remote: /remote/i.test(j.categories?.location || "") || j.workplaceType === "remote",
    url: j.hostedUrl, published: j.createdAt ? new Date(j.createdAt).toISOString() : null,
    department: j.categories?.team || null,
  }));
}

const cache = new Map(); // key -> {t, jobs}
const TTL = 10 * 60 * 1000;

export async function fetchBoard(ats, slug) {
  if (!ENDPOINTS[ats]) throw new Error(`unsupported ats: ${ats}`);
  const key = `${ats}:${slug}`;
  const hit = cache.get(key);
  if (hit && Date.now() - hit.t < TTL) return hit.jobs;
  const r = await fetch(ENDPOINTS[ats](slug), { headers: UA, signal: AbortSignal.timeout(15000) });
  if (!r.ok) return [];
  const jobs = normalise(ats, slug, await r.json()).filter((j) => j.url);
  cache.set(key, { t: Date.now(), jobs });
  return jobs;
}

export async function pool(items, n, fn) {
  const out = []; let i = 0;
  await Promise.all(Array.from({ length: n }, async () => {
    while (i < items.length) { const k = i++; try { out[k] = await fn(items[k]); } catch { out[k] = []; } }
  }));
  return out;
}

const words = (s) => s.toLowerCase().split(/[\s,]+/).filter(Boolean);

/** Every keyword must appear in title (+department). Exclude keywords must not. */
export function matches(job, { keywords = [], exclude = [], location = "", remote_only = false }) {
  const hay = `${job.title} ${job.department || ""}`.toLowerCase();
  if (!keywords.every((k) => hay.includes(k.toLowerCase()))) return false;
  if (exclude.some((k) => hay.includes(k.toLowerCase()))) return false;
  if (remote_only && !job.remote) return false;
  if (location) {
    const loc = job.location.toLowerCase();
    if (!words(location).some((w) => loc.includes(w))) return false;
  }
  return true;
}

export async function searchJobs(q, boards = BOARDS) {
  let list = boards;
  if (q.ats) list = list.filter((b) => b.ats === q.ats);
  if (q.companies?.length) {
    const want = q.companies.map((c) => c.toLowerCase());
    list = list.filter((b) => want.includes(b.slug.toLowerCase()));
  }
  const res = await pool(list, 12, (b) => fetchBoard(b.ats, b.slug));
  const jobs = res.flat().filter((j) => matches(j, q));
  jobs.sort((a, b) => String(b.published || "").localeCompare(String(a.published || "")));
  return { boards_scanned: list.length, total: jobs.length, jobs: jobs.slice(0, q.limit ?? 25) };
}

/** Try every supported ATS for a slug; returns the ones that respond with jobs. */
export async function discoverBoard(slug) {
  const found = [];
  for (const ats of SUPPORTED_ATS) {
    try { const jobs = await fetchBoard(ats, slug); if (jobs.length) found.push({ ats, slug, open_roles: jobs.length }); } catch {}
  }
  return found;
}
