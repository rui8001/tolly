#!/usr/bin/env node
import { existsSync, readFileSync, statSync } from "node:fs";
import { extname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

const dataExtensions = new Set([".json", ".jsonl", ".csv", ".db", ".sqlite"]);
const forbidden = [
  /[A-Za-z]:\\Users\\(?!example\\|username\\)/i,
  /\/Users\/(?!example\/|username\/)/i,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /\bsk-[A-Za-z0-9_-]{20,}\b/,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
  /\borg-[A-Za-z0-9]{16,}\b/,
  /Authorization:\s*Bearer\s+[A-Za-z0-9._~-]{12,}/i,
  /Cookie:\s*[^\s=;]+=[^\s;]{8,}/i,
];
export function inspectFile(relative, bytes) {
  const failures = [];
  if (dataExtensions.has(extname(relative).toLowerCase()) && bytes.length > 512_000) {
    failures.push(`${relative}: unusually large tracked data file`);
  }
  if (relative.includes("sample_usage") && bytes.length > 50_000) {
    failures.push(`${relative}: sample fixture exceeds 50 KB`);
  }
  // Binary images/installers are not text. Scan all other tracked content,
  // including documentation, source code and workflow definitions.
  if (bytes.includes(0)) return failures;
  const text = bytes.toString("utf8");
  for (const pattern of forbidden) {
    if (pattern.test(text)) failures.push(`${relative}: sensitive-data pattern detected`);
  }
  return failures;
}

function main() {
 const root = resolve(import.meta.dirname, "..");
 const listed = spawnSync("git", ["ls-files", "-z"], { cwd: root, encoding: "utf8" });
 if (listed.error || listed.status !== 0) throw listed.error || new Error(listed.stderr);
 const failures = [];
 for (const relative of listed.stdout.split("\0").filter(Boolean)) {
  const absolute = resolve(root, relative);
  if (!existsSync(absolute)) continue;
  if (!statSync(absolute).isFile()) continue;
  failures.push(...inspectFile(relative, readFileSync(absolute)));
 }
 if (failures.length) {
  process.stderr.write(`Privacy check failed:\n${failures.map((item) => `- ${item}`).join("\n")}\n`);
  process.exit(1);
 }
 process.stdout.write("Privacy check passed for all tracked text files and data-size limits.\n");
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main();
