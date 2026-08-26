import test from "node:test";
import assert from "node:assert/strict";

import { displayProject } from "../src/project-name.js";

test("hides Windows user directories", () => {
  assert.equal(displayProject("C:\\Users\\alice\\WorkBuddy\\private-project"), "private project");
  assert.equal(displayProject("c-Users-alice-WorkBuddy-2026-08-06-17-31-00"), "WorkBuddy 会话 · 2026-08-06 17:31");
});

test("replaces opaque session identifiers", () => {
  assert.match(displayProject("9ef10ecc-f31b-430c-8ac8-aeb804ecb290"), /^未命名项目 · [0-9A-F]{4}$/);
  assert.match(displayProject("26"), /^未命名项目 · [0-9A-F]{4}$/);
  assert.notEqual(displayProject("26"), displayProject("27"));
});

test("keeps useful project context without the full path", () => {
  assert.equal(displayProject("D:\\GitHub项目\\tolly"), "GitHub项目 / tolly");
  assert.equal(displayProject("hello%20world"), "hello world");
});
