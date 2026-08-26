#!/usr/bin/env node
/** Validate the engine JSON contract without persisting any private usage data. */
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const engineRoot = resolve(import.meta.dirname, "..");

function findPython() {
  const configured = process.env.TALLY_PYTHON;
  const candidates = configured
    ? [[configured, []]]
    : process.platform === "win32"
      ? [["py", ["-3"]], ["python", []], ["python3", []]]
      : [["python3", []], ["python", []]];
  for (const [command, prefix] of candidates) {
    const probe = spawnSync(command, [...prefix, "--version"], { encoding: "utf8" });
    const version = `${probe.stdout || ""}${probe.stderr || ""}`.match(/Python 3\.(\d+)/);
    if (!probe.error && probe.status === 0 && version && Number(version[1]) >= 10) {
      return { command, prefix };
    }
  }
  throw new Error("Python 3.10+ not found. Set TALLY_PYTHON to its executable path.");
}

const { command, prefix } = findPython();
const result = spawnSync(
  command,
  [...prefix, "-m", "engine", "--json", "--no-sync-snapshot"],
  {
    cwd: engineRoot,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  },
);
if (result.error || result.status !== 0) {
  throw result.error || new Error(`engine exited with ${result.status}: ${result.stderr}`);
}

const data = JSON.parse(result.stdout);
const tools = Object.keys(data).filter((key) => !key.startsWith("_"));
if (!data._pricing || !data._daily || !data._projects) {
  throw new Error("engine contract is missing _pricing, _daily, or _projects");
}
if (Object.keys(data._daily).length !== 30) {
  throw new Error(`expected a 30-day window, received ${Object.keys(data._daily).length}`);
}
for (const tool of tools) {
  if (!data[tool]?.ranges?.all) throw new Error(`${tool} is missing ranges.all`);
}

process.stdout.write(
  `[verify] OK — ${tools.length} collectors, ${Object.keys(data._daily).length} daily buckets; no usage data written to disk.\n`,
);
