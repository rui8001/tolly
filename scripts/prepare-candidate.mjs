// Candidate-only version stamp. No tags, commits or releases are created.
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const versionFiles = [
  'tally-win/package.json', 'tally-win/src-tauri/tauri.conf.json',
  'tally-win/src-tauri/Cargo.toml', 'tally-win/src-tauri/Cargo.lock',
  'tally-engine/pyproject.toml', 'tally-engine/engine/__init__.py',
];

export function candidateEdits(sources, from = '1.2.0', to = '1.2.1') {
  if (from !== '1.2.0' || to !== '1.2.1') throw new Error('Review the next candidate version explicitly');
  return Object.fromEntries(versionFiles.map((path) => {
    const source = sources[path];
    if (typeof source !== 'string') throw new Error(`Missing version file: ${path}`);
    let pattern;
    if (path.endsWith('.json')) {
      if (JSON.parse(source).version !== from) throw new Error(`Unexpected version: ${path}`);
      pattern = /("version"\s*:\s*")([^"\n]+)(")/;
    } else if (path.endsWith('Cargo.lock')) {
      pattern = /(\[\[package\]\]\s+name = "tolly-windows"\s+version = ")([^"\n]+)(")/;
    } else if (path.endsWith('.py')) {
      pattern = /(^__version__\s*=\s*["'])([^"'\n]+)(["'])/m;
    } else {
      pattern = /(^version\s*=\s*")([^"\n]+)(")/m;
    }
    const match = source.match(pattern);
    if (!match || match[2] !== from) throw new Error(`Unexpected version: ${path}`);
    return [path, source.replace(pattern, (_all, before, _old, after) => before + to + after)];
  }));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.env.GITHUB_ACTIONS !== 'true') throw new Error('Candidate stamping is restricted to disposable CI checkouts');
  const root = resolve(import.meta.dirname, '..');
  const sources = Object.fromEntries(versionFiles.map(path => [path, readFileSync(resolve(root, path), 'utf8')]));
  const edits = candidateEdits(sources); // validate every file before writing any
  for (const [path, text] of Object.entries(edits)) writeFileSync(resolve(root, path), text);
  console.log('Candidate-only version: 1.2.1; no public release created');
}
