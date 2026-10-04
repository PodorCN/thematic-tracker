#!/usr/bin/env node
/**
 * validate_pm_review.mjs — machine-checks the independent PM review.
 *
 *   node scripts/validate_pm_review.mjs \
 *     --candidate review/<date>/candidate.json \
 *     --review    review/<date>/pm-review.json \
 *     [--flags review/<date>/structural-flags.json] \
 *     [--require-approved]
 *
 * Checks (no English prose matching, only structure + hashes + severity math):
 *  - review parses, has exactly the schema keys, checks has exactly 6 keys
 *  - candidate_sha256 == sha256(candidate file BYTES)
 *  - candidate.snapshot_date == review.snapshot_date
 *  - reviewer != operator, neither banned (self/me/operator/reviewer/ai)
 *  - verdict/severity/checks coherence:
 *      APPROVED => zero critical/major findings AND all 6 checks pass
 *      REVISE   => at least one critical/major finding OR one failed check
 *  - every finding has field + issue + evidence (min lengths; evidence must
 *    contain a verifiable pointer: URL, .json path, or quoted value)
 *  - if --flags given: every machine flag (code+field) is dispositioned
 */
import fs from "node:fs";
import crypto from "node:crypto";

const args = process.argv.slice(2);
function opt(name) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
}
const candidatePath = opt("--candidate");
const reviewPath = opt("--review");
const flagsPath = opt("--flags");
const requireApproved = args.includes("--require-approved");

if (!candidatePath || !reviewPath) {
  console.error("usage: validate_pm_review.mjs --candidate <json> --review <json> [--flags <json>] [--require-approved]");
  process.exit(2);
}

const problems = [];
const sha256bytes = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");

let candidate;
try {
  candidate = JSON.parse(fs.readFileSync(candidatePath, "utf8"));
} catch (e) {
  console.error(`✗ candidate is not valid JSON: ${e.message}`);
  process.exit(1);
}
let review;
try {
  review = JSON.parse(fs.readFileSync(reviewPath, "utf8"));
} catch (e) {
  console.error(`✗ review is not valid JSON: ${e.message}`);
  process.exit(1);
}

// --- schema keys ---
const TOP = ["schema_version", "reviewer", "operator", "reviewed_at", "snapshot_date", "candidate_sha256", "verdict", "executive_summary", "checks", "findings", "flags_dispositioned"];
for (const k of TOP) if (!(k in review)) problems.push(`review missing top key "${k}"`);
for (const k of Object.keys(review)) if (!TOP.includes(k)) problems.push(`review has unknown top key "${k}"`);
if (review.schema_version !== "1.0") problems.push(`schema_version must be "1.0"`);
if (typeof review.executive_summary !== "string" || review.executive_summary.length < 20)
  problems.push("executive_summary must be >= 20 chars (say what you approved and what you checked)");

const CHECKS = ["official_policy", "pricing", "drivers", "market_validation", "freshness", "decision_usefulness"];
if (review.checks && typeof review.checks === "object") {
  for (const k of CHECKS) if (!(k in review.checks)) problems.push(`checks missing "${k}"`);
  for (const k of Object.keys(review.checks || {})) {
    if (!CHECKS.includes(k)) problems.push(`checks has unknown key "${k}"`);
    else if (!["pass", "fail"].includes(review.checks[k])) problems.push(`checks.${k} must be pass|fail`);
  }
} else {
  problems.push("checks must be an object with 6 keys");
}

// --- sha binding ---
const actualSha = sha256bytes(candidatePath);
if (review.candidate_sha256 !== actualSha) {
  problems.push(`candidate_sha256 mismatch: review says ${(review.candidate_sha256 || "").slice(0, 12)}… but candidate bytes hash to ${actualSha.slice(0, 12)}… (re-freeze after any edit)`);
}
if (candidate.snapshot_date && review.snapshot_date && candidate.snapshot_date !== review.snapshot_date) {
  problems.push(`snapshot_date mismatch: candidate ${candidate.snapshot_date} vs review ${review.snapshot_date}`);
}

// --- role separation ---
const norm = (s) => String(s || "").trim().toLowerCase();
const banned = new Set(["self", "me", "operator", "reviewer", "ai", "agent", "opencode"]);
if (!review.reviewer || String(review.reviewer).trim().length < 3) problems.push("reviewer must be a named identity (>=3 chars)");
if (!review.operator || String(review.operator).trim().length < 3) problems.push("operator must be a named identity (>=3 chars)");
if (norm(review.reviewer) === norm(review.operator)) problems.push("reviewer and operator must be different people/models (self-review is rejected)");
if (banned.has(norm(review.reviewer))) problems.push(`reviewer "${review.reviewer}" is a banned placeholder — sign with a real name/model`);
if (banned.has(norm(review.operator))) problems.push(`operator "${review.operator}" is a banned placeholder`);

// --- findings ---
const SEV = ["critical", "major", "minor"];
const DISP = ["fixed", "must_fix", "accepted", "next_cycle"];
if (!Array.isArray(review.findings)) {
  problems.push("findings must be an array");
} else {
  review.findings.forEach((f, i) => {
    const pre = `findings[${i}]`;
    if (!f || typeof f !== "object") { problems.push(`${pre} must be an object`); return; }
    for (const k of ["severity", "field", "issue", "evidence", "disposition"]) {
      if (!(k in f)) problems.push(`${pre} missing "${k}"`);
    }
    if (f.severity && !SEV.includes(f.severity)) problems.push(`${pre}.severity must be critical|major|minor`);
    if (f.disposition && !DISP.includes(f.disposition)) problems.push(`${pre}.disposition must be fixed|must_fix|accepted|next_cycle`);
    for (const k of ["field", "issue", "evidence"]) {
      if (typeof f[k] !== "string" || f[k].trim().length < (k === "field" ? 3 : 10))
        problems.push(`${pre}.${k} too short — give a grep-able pointer (field path / URL / quote)`);
    }
    if (typeof f.evidence === "string" && f.evidence.trim().length >= 10) {
      const e = f.evidence;
      const verifiable = /https?:\/\/|candidate\.|drivers\.|meetings\.|calendar|pm-review|["'][^"']{3,}["']|\d{4}-\d{2}-\d{2}|\d+\.\d+%?/.test(e);
      if (!verifiable) problems.push(`${pre}.evidence has no verifiable pointer (need URL, field path, number, or quote)`);
    }
  });
}

// --- verdict coherence ---
const critMaj = (review.findings || []).filter((f) => f.severity === "critical" || f.severity === "major");
const anyFail = Object.values(review.checks || {}).includes("fail");
if (review.verdict === "APPROVED") {
  if (critMaj.length) problems.push(`verdict APPROVED but ${critMaj.length} critical/major finding(s) open — must be REVISE`);
  if (anyFail) problems.push("verdict APPROVED but at least one check is fail — must be REVISE");
  if ("operator_instructions" in review) problems.push('APPROVED review must not carry operator_instructions (put it in executive_summary)');
} else if (review.verdict === "REVISE") {
  if (!critMaj.length && !anyFail && !(review.findings || []).length)
    problems.push("verdict REVISE but no findings and all checks pass — give a reason");
} else {
  problems.push('verdict must be APPROVED|REVISE');
}
if (requireApproved && review.verdict !== "APPROVED") {
  problems.push(`gate requires APPROVED but verdict is ${review.verdict}`);
}

// --- flags coverage (optional) ---
if (flagsPath) {
  let flags = [];
  try {
    flags = JSON.parse(fs.readFileSync(flagsPath, "utf8"));
    if (!Array.isArray(flags)) throw new Error("flags file must be a JSON array");
  } catch (e) {
    problems.push(`cannot read flags file: ${e.message}`);
    flags = null;
  }
  if (flags) {
    const disp = review.flags_dispositioned || [];
    for (const fl of flags) {
      const hit = disp.find((d) => d.code === fl.code && d.field === fl.field);
      if (!hit) problems.push(`machine flag uncovered: [${fl.code}] ${fl.field} — reviewer must disposition it in flags_dispositioned`);
      else if (!hit.disposition || String(hit.disposition).trim().length < 5)
        problems.push(`flags_dispositioned [${fl.code}] ${fl.field} needs a real disposition (>=5 chars)`);
    }
  }
}

if (problems.length) {
  console.error("✗ pm-review INVALID:");
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log(`✓ pm-review valid (${review.verdict}, ${(review.findings || []).length} findings, sha ${actualSha.slice(0, 12)}…)`);
