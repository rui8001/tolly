import assert from "node:assert/strict";
import test from "node:test";

import { projectEntries } from "../src/project-data.js";

const bucket = (inTokens, cost, sessions = []) => ({
  in: inTokens, out: 0, cr: 0, cw: 0, cost, sessions,
});

test("project rows use the selected period and hide empty projects", () => {
  const projects = {
    "D:\\GitHub项目\\tolly": {
      tools: ["codex"], last: "2026-09-02",
      ranges: { today: bucket(120, 1.2, ["a"]), week: bucket(500, 4.8, ["a", "b"]) },
    },
    empty: { tools: ["codex"], ranges: { today: bucket(0, 0) } },
  };

  const today = projectEntries(projects, "today");
  assert.equal(today.length, 1);
  assert.equal(today[0].tokens, 120);
  assert.equal(today[0].sessions, 1);
  assert.equal(today[0].name, "GitHub项目 / tolly");
});

test("equivalent display names are merged across tools", () => {
  const projects = {
    "hello_world": { tools: ["codex"], last: "2026-09-01", ranges: { week: bucket(10, 0.1, ["a"]) } },
    "hello-world": { tools: ["workbuddy"], last: "2026-09-02", ranges: { week: bucket(20, 0.2, ["b"]) } },
  };

  const rows = projectEntries(projects, "week");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].tokens, 30);
  assert.deepEqual(rows[0].tools, ["codex", "workbuddy"]);
  assert.equal(rows[0].last, "2026-09-02");
});
