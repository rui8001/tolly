import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const workflow = await readFile(
  new URL("../../.github/workflows/windows-candidate.yml", import.meta.url),
  "utf8",
);

function eventBlock(eventName, nextEventName) {
  const start = workflow.indexOf(`  ${eventName}:`);
  const end = workflow.indexOf(`  ${nextEventName}:`, start + 1);
  assert.notEqual(start, -1, `${eventName} trigger exists`);
  assert.notEqual(end, -1, `${nextEventName} trigger exists`);
  return workflow.slice(start, end);
}

test("Windows candidate runs for installer dependency changes on PR and main", () => {
  const pullRequest = eventBlock("pull_request", "workflow_dispatch");
  const push = eventBlock("push", "pull_request");

  for (const path of [
    "tally-win/package.json",
    "tally-win/pnpm-lock.yaml",
    "tally-win/src-tauri/**",
  ]) {
    assert.ok(pullRequest.includes(`'${path}'`), `PR trigger includes ${path}`);
    assert.ok(push.includes(`'${path}'`), `main push trigger includes ${path}`);
  }
});
