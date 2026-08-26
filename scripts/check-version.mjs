#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relative) => readFileSync(resolve(root, relative), "utf8");
const jsonVersion = (relative) => JSON.parse(read(relative)).version;
const tomlVersion = (relative, packageName) => {
  const source = read(relative);
  const section = packageName
    ? source.match(new RegExp(`name = "${packageName}"[\\s\\S]*?version = "([^"]+)"`))
    : source.match(/^version\s*=\s*"([^"]+)"/m);
  if (!section) throw new Error(`Could not read version from ${relative}`);
  return section[1];
};

const versions = new Map([
  ["tally-win/package.json", jsonVersion("tally-win/package.json")],
  ["tally-win/src-tauri/tauri.conf.json", jsonVersion("tally-win/src-tauri/tauri.conf.json")],
  ["tally-win/src-tauri/Cargo.toml", tomlVersion("tally-win/src-tauri/Cargo.toml")],
  ["tally-win/src-tauri/Cargo.lock", tomlVersion("tally-win/src-tauri/Cargo.lock", "tolly-windows")],
  ["tally-engine/pyproject.toml", tomlVersion("tally-engine/pyproject.toml")],
]);

const unique = new Set(versions.values());
if (unique.size !== 1) {
  const details = [...versions].map(([file, version]) => `- ${file}: ${version}`).join("\n");
  throw new Error(`Version mismatch:\n${details}`);
}

const version = unique.values().next().value;
if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) {
  throw new Error(`Unsupported version format: ${version}`);
}

const tagIndex = process.argv.indexOf("--tag");
const tag = tagIndex >= 0 ? process.argv[tagIndex + 1] : undefined;
if (tagIndex >= 0 && !tag) throw new Error("--tag requires a value");
if (tag && tag !== `v${version}`) {
  throw new Error(`Tag ${tag} does not match source version v${version}`);
}

process.stdout.write(`Version check passed: ${version}${tag ? ` (${tag})` : ""}\n`);
