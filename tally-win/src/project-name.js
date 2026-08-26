const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const OPAQUE_RE = /^[0-9a-f]{24,}$/i;

function anonymousLabel(source) {
  let hash = 2166136261;
  for (const char of String(source)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return `未命名项目 · ${(hash >>> 0).toString(16).slice(-4).toUpperCase().padStart(4, "0")}`;
}

export function displayProject(input) {
  let value = String(input || "").trim();
  try { value = decodeURIComponent(value); } catch (_) { /* 保留原值 */ }
  if (!value || /^\d+$/.test(value) || UUID_RE.test(value) || OPAQUE_RE.test(value)) {
    return anonymousLabel(value);
  }

  value = value.replace(/\\/g, "/");
  value = value.replace(/^[a-z]:\/users\/[^/]+\/?/i, "");

  const sluggedUserPath = value.match(/^[a-z][-_ ]+users[-_ ]+[^-_ /]+[-_ ]+(.+)$/i);
  if (sluggedUserPath) value = sluggedUserPath[1];
  value = value.replace(/^[a-z][-_ ]+(?:desktop[-_ ]+)?/i, "");

  const timestamp = value.match(/workbuddy[-_ ]+(\d{4})[-_ ]+(\d{2})[-_ ]+(\d{2})[-_ ]+(\d{2})[-_ ]+(\d{2})/i);
  if (timestamp) {
    return `WorkBuddy 会话 · ${timestamp[1]}-${timestamp[2]}-${timestamp[3]} ${timestamp[4]}:${timestamp[5]}`;
  }

  const parts = value.split("/").filter(Boolean);
  if (parts.length > 2) value = parts.slice(-2).join(" / ");
  else value = parts.join(" / ");

  value = value
    .replace(/^(?:desktop|workbuddy)\s*[/_-]\s*/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!value || /^\d+$/.test(value) || UUID_RE.test(value.replace(/ /g, "-"))) {
    return anonymousLabel(input);
  }
  return value.length > 72 ? `${value.slice(0, 71)}…` : value;
}
