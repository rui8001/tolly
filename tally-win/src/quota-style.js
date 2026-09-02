const FALLBACK_PRIMARY = "#8b5cf6";

function normalizeHex(color) {
  const value = String(color || "").trim();
  return /^#[0-9a-f]{6}$/i.test(value) ? value.toLowerCase() : FALLBACK_PRIMARY;
}

function mixWithWhite(color, amount) {
  const value = normalizeHex(color).slice(1);
  const channels = [0, 2, 4].map((offset) => parseInt(value.slice(offset, offset + 2), 16));
  const mixed = channels.map((channel) => Math.round(channel + (255 - channel) * amount));
  return `#${mixed.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

/** Return the quota fill gradient for the remaining percentage. */
export function quotaGradient(percent, primaryColor) {
  const value = Math.min(Math.max(Number(percent) || 0, 0), 100);
  let start;
  let end;
  if (value >= 50) {
    end = normalizeHex(primaryColor);
    start = mixWithWhite(end, 0.28);
  } else if (value >= 30) {
    start = "#ffe58a";
    end = "#f2b705";
  } else if (value >= 10) {
    start = "#ffbd66";
    end = "#f28c28";
  } else {
    start = "#ff8585";
    end = "#e5484d";
  }
  return `linear-gradient(90deg, ${start} 0%, ${end} 100%)`;
}
