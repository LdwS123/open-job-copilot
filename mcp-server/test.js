import test from "node:test";
import assert from "node:assert/strict";
import { matches, normalise } from "./lib.js";

test("matches: keywords, exclude, location, remote", () => {
  const j = { title: "Business Development Representative", department: "Sales", location: "Paris, France", remote: false };
  assert.ok(matches(j, { keywords: ["business", "development"] }));
  assert.ok(!matches(j, { keywords: ["business"], exclude: ["representative"] }));
  assert.ok(matches(j, { location: "paris london" }));
  assert.ok(!matches(j, { location: "berlin" }));
  assert.ok(!matches(j, { remote_only: true }));
});

test("normalise: lever + greenhouse + ashby shapes", () => {
  assert.equal(normalise("lever", "x", [{ text: "SDR", hostedUrl: "u", categories: { location: "Remote" } }])[0].remote, true);
  assert.equal(normalise("greenhouse", "x", { jobs: [{ title: "T", absolute_url: "u", location: { name: "Paris" } }] })[0].location, "Paris");
  assert.equal(normalise("ashby", "x", { jobs: [{ title: "T", jobUrl: "u", location: "Berlin", isRemote: true }] })[0].remote, true);
});

import { safeUrl } from "./lib.js";
test("safeUrl: only https on ATS hosts", () => {
  assert.ok(safeUrl("https://jobs.lever.co/acme/123"));
  assert.equal(safeUrl("https://evil.example/apply"), null);
  assert.equal(safeUrl("http://jobs.lever.co/x"), null);
  assert.equal(safeUrl("https://jobs.lever.co@evil.example/x"), null);
  assert.equal(safeUrl("javascript:alert(1)"), null);
});
