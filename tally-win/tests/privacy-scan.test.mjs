import { test } from "node:test";
import assert from "node:assert/strict";
import { inspectFile } from "../../scripts/check-privacy.mjs";

test("detects synthetic credentials across source, docs and workflows", () => {
  const samples = ["sk-" + "a".repeat(24), "ghp_" + "a".repeat(24),
    "github_pat_" + "a".repeat(24), "org-" + "a".repeat(24),
    "Authorization: " + "Bearer " + "a".repeat(24), "Cookie: " + "session=" + "a".repeat(24)];
  for (const path of ["README.md", "engine.py", "main.rs", "src/app.js", ".github/workflows/ci.yml"])
    for (const value of samples) {
      const issues = inspectFile(path, Buffer.from(value));
      assert.ok(issues.length > 0, path);
      assert.ok(issues.every(issue => !issue.includes(value)), "do not print sensitive values");
    }
});
test("finds private path and key material without embedding them in fixtures", () => {
  const samples = ["/" + "Users/" + "real-person/project", "-----BEGIN " + "PRIVATE KEY-----"];
  for (const value of samples) assert.ok(inspectFile("notes.md", Buffer.from(value)).length);
});
test("allows safe text and binary assets, retains size limits", () => {
  assert.deepEqual(inspectFile("README.md", Buffer.from("Use a private API key from your environment.")), []);
  assert.deepEqual(inspectFile("icon.png", Buffer.from([137, 80, 0, 1])), []);
  assert.ok(inspectFile("sample_usage.json", Buffer.alloc(51_000, 32)).length);
  assert.ok(inspectFile("usage.db", Buffer.alloc(513_000)).length);
});
