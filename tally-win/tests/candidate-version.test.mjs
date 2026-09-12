import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { candidateEdits, versionFiles } from '../../scripts/prepare-candidate.mjs';

const root = resolve(import.meta.dirname, '../..');
const sources = () => Object.fromEntries(versionFiles.map(path => [path, readFileSync(resolve(root, path), 'utf8')]));

test('candidate stamps all six version contracts without editing the input', () => {
  const inputs = sources();
  // Tests also run inside the already stamped candidate build.
  for (const path of versionFiles) inputs[path] = inputs[path].replaceAll('1.2.1', '1.2.0');
  const before = structuredClone(inputs);
  const edits = candidateEdits(inputs);
  assert.deepEqual(inputs, before);
  assert.equal(Object.keys(edits).length, 6);
  for (const path of versionFiles) assert.notEqual(edits[path], inputs[path]);
  assert.equal(JSON.parse(edits[versionFiles[0]]).version, '1.2.1');
  assert.match(edits[versionFiles[3]], /name = "tolly-windows"\s+version = "1\.2\.1"/);
});

test('candidate rejects missing or divergent versions before producing edits', () => {
  const inputs = sources();
  for (const path of versionFiles) inputs[path] = inputs[path].replaceAll('1.2.1', '1.2.0');
  for (const path of versionFiles) {
    assert.throws(() => candidateEdits({ ...inputs, [path]: undefined }), /Missing/);
    assert.throws(() => candidateEdits({ ...inputs, [path]: inputs[path].replaceAll('1.2.0', '1.9.0') }), /Unexpected/);
  }
});

test('candidate cannot silently select a different release version', () => {
  assert.throws(() => candidateEdits(sources(), '1.2.0', '2.0.0'), /explicitly/);
});
