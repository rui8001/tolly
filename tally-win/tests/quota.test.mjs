import assert from "node:assert/strict";
import test from "node:test";

import { selectQuota } from "../src/quota.js";

test("weekly provider balance takes priority over credits", () => {
  const result = selectQuota({ quota: {
    source: "local_log",
    weekly: { used_percent: 27.5, resets_at: 1_800_000_000 },
    credits: { remaining: 12.5 },
  } });

  assert.equal(result.kind, "weekly");
  assert.equal(result.label, "周余额");
  assert.equal(result.valueText, "73%");
  assert.equal(result.remainingPercent, 72.5);
});

test("credits are the fallback when no weekly balance exists", () => {
  const result = selectQuota({ quota: { credits: { remaining: "18.25" } } });

  assert.equal(result.kind, "credits");
  assert.equal(result.label, "剩余积分");
  assert.equal(result.valueText, "18.25");
});

test("missing or invalid quota stays hidden", () => {
  assert.equal(selectQuota({}), null);
  assert.equal(selectQuota({ quota: { credits: { remaining: "unknown" } } }), null);
  assert.equal(selectQuota({ quota: {
    weekly: { remaining_percent: 80, resets_at: 1 },
  } }), null);
});

test("model-specific fallback is not mislabeled as the account balance", () => {
  const result = selectQuota({ quota: {
    limit_id: "codex_bengalfox",
    limit_name: "GPT-5.3-Codex-Spark",
    weekly: { remaining_percent: 100, resets_at: 1_900_000_000 },
  } });

  assert.equal(result.label, "GPT-5.3-Codex-Spark 周余额");
});
