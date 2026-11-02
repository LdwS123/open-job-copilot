#!/usr/bin/env node
// open-job-copilot MCP server: free, keyless job search over public ATS APIs.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { BOARDS, SUPPORTED_ATS, searchJobs, fetchBoard, discoverBoard } from "./lib.js";

const server = new McpServer({ name: "open-job-copilot", version: "0.1.0" });
const text = (o) => ({ content: [{ type: "text", text: typeof o === "string" ? o : JSON.stringify(o, null, 2) }] });

server.registerTool("search_jobs", {
  description:
    "Search live job postings across ~300 curated startup / scale-up / big-tech boards (Ashby, Greenhouse, Lever; many YC and a16z-backed companies). " +
    "Data comes straight from each company's public careers API. Returns title, company, location, remote flag, apply URL, publish date.",
  inputSchema: {
    keywords: z.array(z.string()).default([]).describe("All must appear in the job title, e.g. ['sales','development']"),
    exclude: z.array(z.string()).default([]).describe("Words that must NOT appear, e.g. ['senior','staff','director']"),
    location: z.string().default("").describe("Any of these words must appear in the location, e.g. 'paris france europe emea'"),
    remote_only: z.boolean().default(false),
    ats: z.enum(SUPPORTED_ATS).optional().describe("Restrict to one ATS"),
    companies: z.array(z.string()).optional().describe("Restrict to these board slugs, e.g. ['stripe','linear']"),
    limit: z.number().int().min(1).max(100).default(25),
  },
}, async (args) => text(await searchJobs(args)));

server.registerTool("get_company_jobs", {
  description: "List every open role of one company board.",
  inputSchema: { ats: z.enum(SUPPORTED_ATS), slug: z.string().describe("Board slug, the part after the host, e.g. 'linear' in jobs.ashbyhq.com/linear") },
}, async ({ ats, slug }) => text(await fetchBoard(ats, slug)));

server.registerTool("discover_board", {
  description: "Given a company slug, check Ashby, Greenhouse and Lever and report which one hosts its careers board.",
  inputSchema: { slug: z.string() },
}, async ({ slug }) => text(await discoverBoard(slug)));

server.registerTool("list_boards", {
  description: "List the curated boards this server searches (ats + slug).",
  inputSchema: { ats: z.enum(SUPPORTED_ATS).optional() },
}, async ({ ats }) => text(ats ? BOARDS.filter((b) => b.ats === ats) : BOARDS));

await server.connect(new StdioServerTransport());
