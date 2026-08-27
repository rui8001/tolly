function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clampPercent(value) {
  const number = finiteNumber(value);
  return number === null ? null : Math.min(Math.max(number, 0), 100);
}

function resetHasPassed(value) {
  const seconds = finiteNumber(value);
  return seconds !== null && seconds > 0 && seconds * 1000 < Date.now();
}

export function formatQuotaNumber(value) {
  const number = finiteNumber(value);
  if (number === null) return "—";
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(number);
}

export function formatQuotaReset(epochSeconds) {
  const seconds = finiteNumber(epochSeconds);
  if (seconds === null || seconds <= 0) return "";
  const date = new Date(seconds * 1000);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(date);
}

export function selectQuota(toolData) {
  const quota = toolData && toolData.quota;
  if (!quota || typeof quota !== "object") return null;

  const weekly = quota.weekly;
  if (weekly && typeof weekly === "object" && !resetHasPassed(weekly.resets_at)) {
    let remaining = clampPercent(weekly.remaining_percent);
    if (remaining === null) {
      const used = clampPercent(weekly.used_percent);
      if (used !== null) remaining = 100 - used;
    }
    if (remaining !== null) {
      return {
        kind: "weekly",
        label: quota.limit_id && quota.limit_id !== "codex" && quota.limit_name
          ? `${quota.limit_name} 周余额` : "周余额",
        valueText: `${remaining.toFixed(0)}%`,
        remainingPercent: remaining,
        resetText: formatQuotaReset(weekly.resets_at),
        source: quota.source || "provider",
      };
    }
  }

  const credits = quota.credits;
  if (credits && typeof credits === "object") {
    if (credits.unlimited === true) {
      return { kind: "credits", label: "剩余积分", valueText: "不限量", source: quota.source || "provider" };
    }
    const remaining = finiteNumber(credits.remaining);
    if (remaining !== null && remaining >= 0) {
      const total = finiteNumber(credits.total);
      const pct = total !== null && total > 0 ? clampPercent(remaining / total * 100) : null;
      return {
        kind: "credits",
        label: "剩余积分",
        valueText: formatQuotaNumber(remaining),
        remainingPercent: pct,
        resetText: formatQuotaReset(credits.resets_at),
        source: quota.source || "provider",
      };
    }
  }
  return null;
}
