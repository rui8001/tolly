#!/usr/bin/env node
import { existsSync, readFileSync, statSync } from "node:fs";
import { extname, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const listed = spawnSync("git", ["ls-files"], { cwd: root, encoding: "utf8" });
if (listed.error || listed.status !== 0) throw listed.error || new Error(listed.stderr);

const dataExtensions = new Set([".json", ".jsonl", ".csv", ".db", ".sqlite"]);
const forbidden = [
  /[A-Za-z]:\\Users\\(?!example\\|username\\)/i,
  /\/Users\/(?!example\/|username\/)/i,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
];
const failures = [];
for (const relative of listed.stdout.split(/\r?\n/).filter(Boolean)) {
  if (!dataExtensions.has(extname(relative).toLowerCase())) continue;
  const absolute = resolve(root, relative);
  if (!existsSync(absolute)) continue;
  if (statSync(absolute).size > 512_000) {
    failures.push(`${relative}: unusually large tracked data file`);
    continue;
  }
  const text = readFileSync(absolute, "utf8");
  if (relative.includes("sample_usage") && Buffer.byteLength(text) > 50_000) {
    failures.push(`${relative}: sample fixture exceeds 50 KB`);
  }
  for (const pattern of forbidden) {
    if (pattern.test(text)) failures.push(`${relative}: matched ${pattern}`);
  }
}

if (failures.length) {
  process.stderr.write(`Privacy check failed:\n${failures.map((item) => `- ${item}`).join("\n")}\n`);
  process.exit(1);
}
process.stdout.write("Privacy check passed for tracked data files.\n");
