import assert from "node:assert/strict";
import test from "node:test";

import { quotaGradient } from "../src/quota-style.js";

test("quota gradient follows four remaining-balance bands", () => {
  assert.match(quotaGradient(80, "#5b8def"), /#5b8def/);
  assert.match(quotaGradient(50, "#5b8def"), /#5b8def/);
  assert.match(quotaGradient(49.9, "#5b8def"), /#f2b705/);
  assert.match(quotaGradient(30, "#5b8def"), /#f2b705/);
  assert.match(quotaGradient(29.9, "#5b8def"), /#f28c28/);
  assert.match(quotaGradient(10, "#5b8def"), /#f28c28/);
  assert.match(quotaGradient(9.9, "#5b8def"), /#e5484d/);
});

test("quota fill is a real left-to-right gradient", () => {
  assert.match(quotaGradient(46, "#5b8def"), /^linear-gradient\(90deg,/);
});
