import { displayProject } from "./project-name.js";

function number(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function tokenTotal(range) {
  return number(range.in) + number(range.out) + number(range.cr) + number(range.cw);
}

/** Normalize, merge and filter project rows for one selected period. */
export function projectEntries(projects, period) {
  const merged = new Map();
  for (const [rawName, project] of Object.entries(projects || {})) {
    const range = ((project || {}).ranges || {})[period] || {};
    const tokens = tokenTotal(range);
    const cost = number(range.cost);
    const calls = number(range.calls);
    const credits = number(range.credits_used);
    if (tokens <= 0 && cost <= 0 && calls <= 0 && credits <= 0) continue;

    const name = displayProject(rawName);
    let row = merged.get(name);
    if (!row) {
      row = {
        name, tokens: 0, cost: 0, calls: 0, credits: 0,
        tools: new Set(), sessions: new Set(), sessionCount: 0, last: null,
      };
      merged.set(name, row);
    }
    row.tokens += tokens;
    row.cost += cost;
    row.calls += calls;
    row.credits += credits;
    for (const tool of (project.tools || [])) row.tools.add(tool);
    const sessionList = Array.isArray(range.sessions) ? range.sessions.map(String) : [];
    for (const session of sessionList) row.sessions.add(session);
    if (!sessionList.length && Number.isFinite(Number(range.sessions))) {
      row.sessionCount += Math.max(Number(range.sessions), 0);
    }
    if (project.last && (!row.last || project.last > row.last)) row.last = project.last;
  }

  return [...merged.values()].map((row) => ({
    ...row,
    tools: [...row.tools].sort(),
    sessions: row.sessions.size + row.sessionCount,
    last: row.last || "—",
  })).sort((a, b) => b.cost - a.cost || b.tokens - a.tokens || b.calls - a.calls || a.name.localeCompare(b.name, "zh-CN"));
}
