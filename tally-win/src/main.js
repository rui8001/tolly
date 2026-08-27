import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import previewUsage from "./sample_usage.json";
import { displayProject } from "./project-name.js";
import { selectQuota } from "./quota.js";

window.__TOLLY_BOOT_STATE__ = "module";
const IS_TAURI = Boolean(window.__TAURI_INTERNALS__);
document.documentElement.classList.toggle("browser-preview", !IS_TAURI);

const TOOL_LABELS = {
  claude: "Claude Code", codex: "Codex", gemini: "Gemini", grok: "Grok",
  qwenwork: "千问办公", doubaowork: "豆包工作", qoderwork: "QoderWork", qoder_ide: "Qoder", qodercli: "Qoder CLI",
  hermes: "Hermes", zcode: "ZCode", mimocode: "MimoCode", openclaw: "OpenClaw",
  pi: "Pi", prime_agent: "Prime Agent", workbuddy: "WorkBuddy", deepseek_harness: "DeepSeek",
  opencode: "OpenCode", qwencode: "Qwen Code", kimicode: "Kimi Code",
};
const TOOL_COLOR_MAP = {
  workbuddy: "#3ec6a0",         // 绿
  qwenwork: "#6fce9f",          // 千问办公 浅绿
  doubaowork: "#4fb8ff",        // 豆包工作 蓝
  qwencode: "#79d6a5",          // Qwen Code 浅绿
  codex: "#5b8def",             // 蓝
  claude: "#d97757",            // Anthropic 橙
  grok: "#b8bcc4",              // 灰
  gemini: "#7e9cff",            // 蓝紫
  qoder_ide: "#f06292",         // 粉
  qodercli: "#ec5f8c",
  qoderwork: "#e8906a",
  deepseek_harness: "#4d6bfe",  // DeepSeek 蓝
  kimicode: "#9aa0ad",
  hermes: "#f2b705",
  zcode: "#26c6da",
  mimocode: "#9ccc65",
  openclaw: "#46c2da",
  pi: "#7e9cff",
  prime_agent: "#b07cf0",
  opencode: "#8d9bf0",
};
function colorFor(tool) {
  if (TOOL_COLOR_MAP[tool]) return TOOL_COLOR_MAP[tool];
  const cols = Object.values(TOOL_COLOR_MAP);
  let h = 0; for (const c of String(tool)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return cols[h % cols.length];
}

const PERIODS = [
  { key: "today", label: "今日" }, { key: "yesterday", label: "昨日" },
  { key: "week", label: "本周" }, { key: "last_week", label: "上周" },
  { key: "month", label: "本月" }, { key: "year", label: "本年" },
];
const periodLabel = (k) => (PERIODS.find((p) => p.key === k) || {}).label || k;

const VIEWS = [
  { key: "usage", label: "概览" }, { key: "projects", label: "项目" }, { key: "wrapped", label: "回顾" },
];

let usageCache = null;
let settingsCache = { hidden_tools: [], refresh_seconds: 30, qwenwork_quota_enabled: false };
let currentPeriod = "today";
let currentView = "usage";
let usingFallback = false;

/* ---------------- helpers ---------------- */
const $ = (id) => document.getElementById(id);
function human(n) {
  n = Number(n) || 0;
  if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(Math.round(n));
}
function fmtCost(c) { return "$" + (Number(c || 0)).toFixed(2); }
function fmtPercent(value) {
  const pct = Math.min(Math.max(Number(value) || 0, 0), 100);
  return pct > 99 && pct < 100 ? pct.toFixed(1) + "%" : pct.toFixed(0) + "%";
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function relDate(d) {
  if (!d || d === "—") return "—";
  const days = Math.round((Date.now() - new Date(d + "T00:00:00")) / 86400000);
  if (days <= 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 30) return days + " 天前";
  if (days < 365) return Math.round(days / 30) + " 个月前";
  return Math.round(days / 365) + " 年前";
}
function tokensOf(r) { return (r.in || 0) + (r.out || 0) + (r.cr || 0) + (r.cw || 0); }

/* ---------------- data contract ---------------- */
function getRange(data, period) { return ((data && data.ranges) || {})[period] || {}; }
function presentTools() {
  if (!usageCache) return [];
  return Object.keys(usageCache).filter((k) => !k.startsWith("_"));
}

/* ---------------- 设置 ---------------- */
async function loadSettings() {
  try {
    const s = IS_TAURI
      ? await invoke("get_settings")
      : JSON.parse(localStorage.getItem("tolly-settings") || "{}");
    settingsCache = {
      hidden_tools: Array.isArray(s.hidden_tools) ? s.hidden_tools : [],
      refresh_seconds: [15, 30, 60, 120].includes(Number(s.refresh_seconds)) ? Number(s.refresh_seconds) : 30,
      qwenwork_quota_enabled: s.qwenwork_quota_enabled === true,
    };
  } catch (e) { /* 无设置文件时用默认 */ }
}
async function saveSettings() {
  const serializable = {
    hidden_tools: settingsCache.hidden_tools || [],
    refresh_seconds: settingsCache.refresh_seconds || 30,
    qwenwork_quota_enabled: settingsCache.qwenwork_quota_enabled === true,
  };
  if (IS_TAURI) await invoke("save_settings", { settings: serializable });
  else localStorage.setItem("tolly-settings", JSON.stringify(serializable));
  await loadSettings();
}

/* ---------------- 卡片渲染 ---------------- */
function hitDonut(pct, color) {
  const r = 9, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
  return `<svg width="26" height="26" viewBox="0 0 26 26">
    <circle cx="13" cy="13" r="${r}" fill="none" stroke="#23262f" stroke-width="3.5"/>
    <circle cx="13" cy="13" r="${r}" fill="none" stroke="${color}" stroke-width="3.5"
      stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" stroke-linecap="round" transform="rotate(-90 13 13)"/>
  </svg>`;
}
function statItem(icon, cls, label, value) {
  return `<div class="stat"><span class="sic ${cls}">${icon}</span><div><div class="sl">${label}</div><div class="sv">${value}</div></div></div>`;
}
function quotaHtml(tool, color) {
  const providerQuota = selectQuota((usageCache || {})[tool]);
  const todayCredits = Number(getRange((usageCache || {})[tool], "today").credits_used || 0);
  const quota = providerQuota || (todayCredits > 0 ? {
    label: "今日消耗",
    valueText: `${todayCredits.toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 积分`,
    remainingPercent: null,
  } : null);
  if (!quota) return "";
  const pct = Number.isFinite(quota.remainingPercent) ? quota.remainingPercent : null;
  const barColor = pct === null || pct >= 50 ? color : pct >= 20 ? "#f2b705" : "#ef6f6f";
  const reset = quota.resetText ? `<span class="cq-reset">重置 ${escapeHtml(quota.resetText)}</span>` : "";
  const bar = pct === null ? "" : `<div class="cq-bar"><i style="width:${pct.toFixed(1)}%;background:${barColor}"></i></div>`;
  return `<div class="cquota"><div class="cq-top"><span>${escapeHtml(quota.label)}</span><strong>${escapeHtml(quota.valueText)}</strong></div>${reset}${bar}</div>`;
}
function modelRows(models, color) {
  const arr = Object.entries(models || {}).map(([m, v]) => ({ m, tokens: tokensOf(v), cost: v.cost || 0 }))
    .sort((a, b) => b.tokens - a.tokens);
  if (!arr.length) return '<div class="mrow"><span class="mname">无模型明细</span></div>';
  const max = Math.max(1, ...arr.map((x) => x.tokens));
  return arr.map((x) => `<div class="mrow"><span class="mname" title="${escapeHtml(x.m)}">${escapeHtml(x.m)}</span>
      <span class="mtok">${human(x.tokens)}</span><span class="mcost">${fmtCost(x.cost)}</span></div>
    <div class="mbar"><i style="width:${(x.tokens / max * 100).toFixed(1)}%;background:${color}"></i></div>`).join("");
}
function renderCard(tool) {
  const data = usageCache[tool] || {};
  const r = getRange(data, currentPeriod);
  const total = tokensOf(r);
  const sessions = Array.isArray(r.sessions) ? r.sessions.length : (r.sessions || 0);
  const color = colorFor(tool);
  const hit = (r.in || 0) + (r.cr || 0) > 0 ? (r.cr || 0) / ((r.in || 0) + (r.cr || 0)) * 100 : null;

  const stats = [];
  stats.push(statItem("$", "cost", "≈成本", fmtCost(r.cost)));
  if (hit !== null) stats.push(`<div class="chit">${hitDonut(hit, color)}<div><div class="sl">命中</div><div class="sv">${fmtPercent(hit)}</div></div></div>`);
  stats.push(statItem("↓", "input", "输入", human(r.in)));
  if ((r.cr || 0) > 0) stats.push(statItem("↯", "cache", "缓存读", human(r.cr)));
  stats.push(statItem("↑", "output", "输出", human(r.out)));
  if ((r.cw || 0) > 0) stats.push(statItem("⇣", "cache-write", "缓存写", human(r.cw)));
  if ((r.reason || 0) > 0) stats.push(statItem("✦", "reason", "推理", human(r.reason)));

  const models = r.models || {};
  const mcount = Object.keys(models).length;

  const balanceHtml = quotaHtml(tool, color);
  const estimated = data.estimated === true;
  const totalLabel = estimated ? `${periodLabel(currentPeriod)} 估算总量` : `${periodLabel(currentPeriod)} 总量`;
  const statusOnly = total === 0 && data.detected === true;
  const statusHtml = statusOnly ? `<div class="detected-note">${escapeHtml(data.note || "已检测到本地数据")}</div>` : "";

  return `<div class="card" style="--tool-color:${color};--tool-tint:${color}22">
    <div class="card-head"><span class="cdot" style="background:${color}"></span>
      <span class="cname">${TOOL_LABELS[tool] || tool}</span>
      ${sessions ? `<span class="csess">${sessions}</span>` : ""}</div>
    <div class="coverview${balanceHtml ? " has-quota" : ""}">
      <div class="ctotal"><div class="cbig">${human(total)}</div>
        <div class="cbig-sub">${totalLabel}</div></div>
      ${balanceHtml}
    </div>
    ${statusHtml || `<div class="cstats">${stats.join("")}</div>
    <button class="cmodels" data-tool="${tool}">● 按模型 (${mcount}) <span class="chev">›</span></button>
    <div class="cmodel-list" id="ml-${tool}">${modelRows(models, color)}</div>`}
  </div>`;
}
function renderUsage() {
  const hidden = new Set(settingsCache.hidden_tools || []);
  const tools = presentTools()
    .filter((t) => !hidden.has(t))
    .map((t) => ({ t, total: tokensOf(getRange(usageCache[t], currentPeriod)), cost: getRange(usageCache[t], currentPeriod).cost || 0,
      credits: Number(getRange(usageCache[t], "today").credits_used || 0), detected: usageCache[t].detected === true }))
    .filter((x) => x.total > 0 || x.cost > 0 || x.credits > 0)
    .sort((a, b) => b.cost - a.cost || b.total - a.total);
  if (!tools.length) return '<div class="empty">该周期暂无用量数据</div>';
  return `<div class="cards">${tools.map((x) => renderCard(x.t)).join("")}</div>`;
}

/* ---------------- 项目 / 回顾 ---------------- */
function renderProjects() {
  const projs = (usageCache && usageCache._projects) || {};
  const entries = Object.keys(projs).map((name) => {
    const p = projs[name], r = (p.ranges && p.ranges.all) || {};
    return { name: displayProject(name), tokens: tokensOf(r), cost: r.cost || 0, tools: p.tools || [], last: p.last || "—",
      sessions: Array.isArray(r.sessions) ? r.sessions.length : 0 };
  }).sort((a, b) => b.cost - a.cost);
  if (!entries.length) return '<div class="empty">暂无项目用量数据</div>';
  const maxCost = Math.max(0.0001, ...entries.map((e) => e.cost));
  const cards = entries.map((e) => {
    const w = (e.cost / maxCost * 100).toFixed(1);
    const tags = (e.tools || []).slice(0, 4).map((t) => `<span class="tag">${TOOL_LABELS[t] || t}</span>`).join("") || '<span class="tag">—</span>';
    return `<div class="proj-card">
      <div class="proj-top"><span class="proj-name">${escapeHtml(e.name)}</span><span class="proj-cost">${fmtCost(e.cost)}</span></div>
      <div class="proj-stat"><div>Token<b>${human(e.tokens)}</b></div><div>会话<b>${e.sessions}</b></div><div>工具<b>${e.tools.length}</b></div></div>
      <div class="proj-share"><i style="width:${w}%"></i></div><div class="tags">${tags}</div>
      <div class="proj-last">最近活跃 · ${relDate(e.last)}</div></div>`;
  }).join("");
  return `<div class="proj-head"><h2 style="margin:0;font-size:16px">项目轨迹</h2><span class="cnt">共 ${entries.length} 个项目</span></div><div class="proj-grid">${cards}</div>`;
}
function dayDiff(a, b) { return Math.round((new Date(b) - new Date(a)) / 86400000); }
function buildWrapped(cache) {
  const tools = Object.keys(cache).filter((k) => !k.startsWith("_"));
  let totIn = 0, totOut = 0, totCr = 0, totCw = 0, totReason = 0, totCost = 0;
  const toolCost = {}, modelCost = {};
  for (const t of tools) {
    const all = (cache[t].ranges && cache[t].ranges.all) || {};
    totIn += all.in || 0; totOut += all.out || 0; totCr += all.cr || 0; totCw += all.cw || 0; totReason += all.reason || 0;
    const c = all.cost || 0; totCost += c; toolCost[t] = c;
    const models = all.models || {};
    for (const m in models) modelCost[m] = (modelCost[m] || 0) + (models[m].cost || 0);
  }
  const total = totIn + totOut + totCr + totCw;
  const topTools = Object.entries(toolCost).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([tool, cost]) => ({ tool, cost }));
  const topModels = Object.entries(modelCost).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([model, cost]) => ({ model, cost }));
  const daily = cache._daily || {};
  const days = Object.keys(daily).sort();
  const topDays = days.map((d) => ({ date: d, cost: daily[d].cost || 0 })).sort((a, b) => b.cost - a.cost).slice(0, 5);
  let best = 0, cur = 0, prev = null;
  for (const d of days) {
    if ((daily[d].cost || 0) > 0) { if (prev !== null && dayDiff(prev, d) === 1) cur++; else cur = 1; best = Math.max(best, cur); prev = d; }
    else { cur = 0; prev = null; }
  }
  return { total, total_cost: totCost, activeTools: Object.values(toolCost).filter((c) => c > 0).length, topTools, topModels, topDays, longest_streak: best, spanDays: days.length };
}
function wrapList(items, max) {
  if (!items.length) return '<div class="empty">暂无数据</div>';
  const m = max || Math.max(0.0001, ...items.map((i) => i.cost));
  return items.map((i) => {
    const name = i.model ? escapeHtml(i.model) : i.date ? escapeHtml(i.date) : (TOOL_LABELS[i.tool] || i.tool);
    return `<div class="wrap-item"><div class="wi-name">${name}<span class="wi-val">${fmtCost(i.cost)}</span></div>
      <div class="wi-bar"><i style="width:${(i.cost / m * 100).toFixed(1)}%"></i></div></div>`;
  }).join("");
}
function renderWrapped() {
  const w = buildWrapped(usageCache);
  if (!w || w.total === 0) return '<div class="empty">暂无用量数据可生成回顾</div>';
  const stats = [
    { v: fmtCost(w.total_cost), l: "总成本" }, { v: String(w.activeTools), l: "活跃工具" },
    { v: w.longest_streak + " 天", l: "最长连续" }, { v: w.spanDays + " 天", l: "统计跨度" },
  ];
  return `<div class="wrap-hero"><div class="eyebrow">AI 编程用量 · 年度回顾</div>
      <div class="big">${human(w.total)}</div>
      <div class="sub">累计消耗 Token · 花费 ${fmtCost(w.total_cost)} · ${w.activeTools} 款工具陪你写过代码</div></div>
    <div class="wrap-grid">${stats.map((s) => `<div class="wrap-col"><div class="wi-name" style="color:var(--muted);font-size:12px">${s.l}</div><div style="font-size:24px;font-weight:800;margin-top:6px">${s.v}</div></div>`).join("")}</div>
    <div class="grid-2">
      <div class="wrap-col"><h3>最烧钱工具</h3><div class="wrap-list">${wrapList(w.topTools)}</div></div>
      <div class="wrap-col"><h3>最常用模型</h3><div class="wrap-list">${wrapList(w.topModels)}</div></div>
      <div class="wrap-col" style="grid-column:1/-1"><h3>最贵单日</h3><div class="wrap-list">${wrapList(w.topDays)}</div></div>
    </div>`;
}

/* ---------------- 设置弹层 ---------------- */
function buildSettingsList() {
  const host = $("settingsList");
  if (!host) return;
  const tools = Object.keys(TOOL_LABELS);
  host.innerHTML = tools.map((t) => {
    const visible = !(settingsCache.hidden_tools || []).includes(t);
    return `<div class="set-item" data-tool="${t}">
      <input type="checkbox" class="sw-visible" ${visible ? "checked" : ""} />
      <div class="si-name"><span class="cdot" style="background:${colorFor(t)}"></span>${TOOL_LABELS[t]}</div>
    </div>`;
  }).join("");
}
function openSettings() {
  const refreshSelect = $("refreshSeconds");
  if (refreshSelect) refreshSelect.value = String(settingsCache.refresh_seconds || 30);
  const qwenQuota = $("qwenworkQuota");
  if (qwenQuota) qwenQuota.checked = settingsCache.qwenwork_quota_enabled === true;
  buildSettingsList();
  $("settingsMask").classList.add("open");
}
function closeSettings() { $("settingsMask").classList.remove("open"); }
function collectSettings() {
  const hidden = [];
  document.querySelectorAll("#settingsList .set-item").forEach((it) => {
    const t = it.dataset.tool;
    if (!it.querySelector(".sw-visible").checked) hidden.push(t);
  });
  settingsCache.hidden_tools = hidden;
  settingsCache.refresh_seconds = Number(document.getElementById("refreshSeconds")?.value || 30);
  settingsCache.qwenwork_quota_enabled = document.getElementById("qwenworkQuota")?.checked === true;
}

/* ---------------- 页脚 ---------------- */
function renderFooter() {
  const hidden = new Set(settingsCache.hidden_tools || []);
  const present = new Set(presentTools().filter((t) => tokensOf(getRange(usageCache[t], "all")) > 0 || usageCache[t].detected));
  const missing = Object.keys(TOOL_LABELS).filter((t) => !hidden.has(t) && !present.has(t));
  const el = $("undetected");
  if (el) {
    el.textContent = missing.length ? `另有 ${missing.length} 款工具未检测到本地数据` : "已检测所有支持的工具";
    el.title = missing.map((t) => TOOL_LABELS[t]).join(" · ");
  }
}
function copySummary() {
  if (!usageCache) return;
  const lines = [`Tolly 用量 · ${periodLabel(currentPeriod)}`];
  presentTools().forEach((t) => {
    const r = getRange(usageCache[t], currentPeriod);
    const tot = tokensOf(r);
    if (tot > 0 || (r.cost || 0) > 0) lines.push(`${TOOL_LABELS[t] || t}: ${human(tot)} tokens, ${fmtCost(r.cost)}`);
  });
  const txt = lines.join("\n");
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).catch(() => {});
}

/* ---------------- 导航 / 渲染 ---------------- */
function buildViewSwitch() {
  const host = $("viewSwitch");
  if (!host) return;
  host.innerHTML = VIEWS.map((v) => `<button class="${v.key === currentView ? "active" : ""}" data-view="${v.key}">${v.label}</button>`).join("");
  host.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    currentView = b.dataset.view;
    host.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
    render();
  }));
}
function buildPeriodTabs() {
  const host = $("periods");
  if (!host) return;
  host.innerHTML = PERIODS.map((p) => `<button class="${p.key === currentPeriod ? "active" : ""}" data-key="${p.key}">${p.label}</button>`).join("");
  host.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    currentPeriod = b.dataset.key;
    host.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
    render();
  }));
}
function render() {
  const content = $("content");
  if (!content) return;
  if (!usageCache) { content.innerHTML = '<div class="empty">正在读取用量…</div>'; return; }
  const periods = $("periods");
  if (periods) periods.style.display = currentView === "usage" ? "flex" : "none";
  try {
    if (currentView === "projects") content.innerHTML = renderProjects();
    else if (currentView === "wrapped") content.innerHTML = renderWrapped();
    else content.innerHTML = renderUsage();
  } catch (e) {
    content.innerHTML = `<div class="empty">渲染出错: ${escapeHtml(String(e))}</div>`;
  }
}

/* ---------------- 数据加载 ---------------- */
async function loadUsage() {
  if (IS_TAURI) {
    const raw = await invoke("get_usage");
    usageCache = typeof raw === "string" ? JSON.parse(raw) : raw;
    usingFallback = false;
  } else {
    usageCache = structuredClone(previewUsage);
    usingFallback = true;
  }
}
async function refresh() {
  const updated = $("updated");
  try {
    await Promise.all([loadUsage(), loadSettings()]);
    scheduleRefresh();
    render();
    renderFooter();
    if (updated) {
      const stamp = new Date().toTimeString().slice(0, 8);
      updated.textContent = (usingFallback ? "示例数据 " : "更新 ") + stamp;
    }
  } catch (e) {
    const content = $("content");
    if (content) content.innerHTML = `<div class="empty">读取失败: ${escapeHtml(String(e))}</div>`;
    if (updated) updated.textContent = "加载失败";
  }
}

/* ---------------- 事件绑定（含动态内容委托） ---------------- */
function bind() {
  const content = $("content");
  if (content) content.addEventListener("click", (e) => {
    const btn = e.target.closest(".cmodels");
    if (btn) {
      const list = $("ml-" + btn.dataset.tool);
      btn.classList.toggle("open");
      if (list) list.classList.toggle("open");
    }
  });
  const refreshBtn = $("refreshBtn"); if (refreshBtn) refreshBtn.addEventListener("click", refresh);
  const copyBtn = $("copyBtn"); if (copyBtn) copyBtn.addEventListener("click", copySummary);
  const quitBtn = $("quitBtn"); if (quitBtn) quitBtn.addEventListener("click", () => {
    if (IS_TAURI) invoke("quit_app");
    else window.close();
  });
  const sb = $("settingsBtn"); if (sb) sb.addEventListener("click", openSettings);
  const sc = $("settingsClose"); if (sc) sc.addEventListener("click", closeSettings);
  const scancel = $("settingsCancel"); if (scancel) scancel.addEventListener("click", closeSettings);
  const smask = $("settingsMask"); if (smask) smask.addEventListener("click", (e) => { if (e.target === smask) closeSettings(); });
  const ssave = $("settingsSave"); if (ssave) ssave.addEventListener("click", async () => {
    collectSettings();
    await saveSettings();
    closeSettings();
    await refresh();
  });
}

buildViewSwitch();
buildPeriodTabs();
bind();
refresh();
if (IS_TAURI) listen("request-refresh", refresh);
window.addEventListener("resize", () => { if (usageCache) render(); });
let refreshTimer = null;
let refreshIntervalSeconds = null;
function scheduleRefresh() {
  const seconds = settingsCache.refresh_seconds || 30;
  if (refreshTimer && refreshIntervalSeconds === seconds) return;
  if (refreshTimer) clearInterval(refreshTimer);
  refreshIntervalSeconds = seconds;
  refreshTimer = setInterval(refresh, seconds * 1000);
}
scheduleRefresh();
