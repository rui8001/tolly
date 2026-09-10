// Predict unsigned installer payloads without modifying any on-disk executable.
// Tauri CLI 2.11.4 bundle.rs patches this marker per bundle, then restores UNK.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const originalMarker = Buffer.from('__TAURI_BUNDLE_TYPE_VAR_UNK');
const markers = {
  msi: Buffer.from('__TAURI_BUNDLE_TYPE_VAR_MSI'),
  nsis: Buffer.from('__TAURI_BUNDLE_TYPE_VAR_NSS'),
};
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');

export function candidateBinaryHashes(bytes) {
  if (!Buffer.isBuffer(bytes)) throw new TypeError('Expected executable bytes as a Buffer');
  const offset = bytes.indexOf(originalMarker);
  if (offset < 0 || bytes.indexOf(originalMarker, offset + 1) !== -1) {
    throw new Error('Expected exactly one unpatched Tauri bundle marker');
  }
  if (Object.values(markers).some(marker => bytes.includes(marker))) {
    throw new Error('Unexpected already-patched Tauri bundle marker');
  }
  const app_sha256_by_installer = Object.fromEntries(Object.entries(markers).map(([kind, marker]) => {
    const payload = Buffer.from(bytes);
    marker.copy(payload, offset);
    return [kind, sha256(payload)];
  }));
  return { app_sha256_unbundled: sha256(bytes), app_sha256_by_installer };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 3) throw new Error('Usage: node scripts/candidate-binary-hashes.mjs <unbundled-exe>');
  console.log(JSON.stringify(candidateBinaryHashes(readFileSync(process.argv[2]))));
}
