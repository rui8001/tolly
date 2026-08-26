import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { delimiter, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const appRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(appRoot, "..");
const engineRoot = join(repoRoot, "tally-engine");
const tauriRoot = join(appRoot, "src-tauri");
const workRoot = join(tauriRoot, ".sidecar-build");
const binariesRoot = join(tauriRoot, "binaries");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: "inherit", ...options });
  if (result.error || result.status !== 0) {
    throw result.error || new Error(`${command} exited with ${result.status}`);
  }
}

function findPython() {
  const configured = process.env.TALLY_PYTHON;
  const candidates = configured
    ? [[configured, []]]
    : process.platform === "win32"
      ? [["py", ["-3"]], ["python", []], ["python3", []]]
      : [["python3", []], ["python", []]];
  for (const [command, prefix] of candidates) {
    const probe = spawnSync(command, [...prefix, "--version"], { stdio: "ignore" });
    if (!probe.error && probe.status === 0) return { command, prefix };
  }
  throw new Error("Python 3.10+ not found. Set TALLY_PYTHON to its executable path.");
}

function rustHost() {
  const result = spawnSync("rustc", ["-vV"], { encoding: "utf8" });
  if (result.error || result.status !== 0) throw new Error("rustc is required to determine the sidecar target triple.");
  const match = result.stdout.match(/^host:\s*(.+)$/m);
  if (!match) throw new Error("Could not read the Rust host target.");
  return match[1].trim();
}

mkdirSync(workRoot, { recursive: true });
mkdirSync(binariesRoot, { recursive: true });
const { command, prefix } = findPython();
const addData = `${join(engineRoot, "pricing.json")}${delimiter}.`;
const addOverrides = `${join(engineRoot, "pricing_overrides.json")}${delimiter}.`;
run(command, [
  ...prefix,
  "-m", "PyInstaller",
  "--noconfirm", "--clean", "--onefile",
  "--name", "tally-engine",
  "--paths", engineRoot,
  "--collect-submodules", "engine.collectors",
  "--add-data", addData,
  "--add-data", addOverrides,
  "--distpath", join(workRoot, "dist"),
  "--workpath", join(workRoot, "work"),
  "--specpath", workRoot,
  join(engineRoot, "sidecar.py"),
], { cwd: repoRoot });

const extension = process.platform === "win32" ? ".exe" : "";
const built = join(workRoot, "dist", `tally-engine${extension}`);
if (!existsSync(built)) throw new Error(`PyInstaller output missing: ${built}`);
const destination = join(binariesRoot, `tally-engine-${rustHost()}${extension}`);
copyFileSync(built, destination);
process.stdout.write(`Sidecar ready: ${destination}\n`);
