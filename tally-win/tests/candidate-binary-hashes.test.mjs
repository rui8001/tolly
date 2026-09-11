import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { candidateBinaryHashes } from '../../scripts/candidate-binary-hashes.mjs';

const fixture = kind => Buffer.concat([
  Buffer.from([0, 255, 17, 66]),
  Buffer.from(`__TAURI_BUNDLE_TYPE_VAR_${kind}`),
  Buffer.from([13, 10, 0, 128, 254]),
]);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

test('hashes full installer-specific payloads without changing the source buffer', () => {
  const source = fixture('UNK');
  const before = Buffer.from(source);
  const result = candidateBinaryHashes(source);
  assert.deepEqual(source, before);
  assert.equal(result.app_sha256_unbundled, hash(source));
  assert.deepEqual(result.app_sha256_by_installer, { msi: hash(fixture('MSI')), nsis: hash(fixture('NSS')) });
  assert.equal(new Set([result.app_sha256_unbundled, ...Object.values(result.app_sha256_by_installer)]).size, 3);
});

test('corruption outside the marker and wrong installer kinds still fail integrity checks', () => {
  const expected = candidateBinaryHashes(fixture('UNK')).app_sha256_by_installer;
  for (const [kind, token] of [['msi', 'MSI'], ['nsis', 'NSS']]) {
    for (const offset of [0, fixture(token).length - 1]) {
      const corrupt = fixture(token);
      corrupt[offset] ^= 1;
      assert.notEqual(hash(corrupt), expected[kind]);
    }
  }
  assert.notEqual(hash(fixture('MSI')), expected.nsis);
  assert.notEqual(hash(fixture('NSS')), expected.msi);
});

test('unknown, missing or ambiguous unpatched markers fail closed', () => {
  for (const source of [Buffer.alloc(0), fixture('NEW'), fixture('MSI'), fixture('NSS'), Buffer.concat([fixture('UNK'), fixture('UNK')])]) {
    assert.throws(() => candidateBinaryHashes(source), /exactly one unpatched/);
  }
  for (const token of ['MSI', 'NSS']) {
    assert.throws(() => candidateBinaryHashes(Buffer.concat([fixture('UNK'), fixture(token)])), /already-patched/);
  }
  assert.throws(() => candidateBinaryHashes('not bytes'), TypeError);
});
