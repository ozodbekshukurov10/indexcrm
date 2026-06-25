export function pickNumber(source: unknown, keys: string[], fallback = 0) {
  if (source && typeof source === "object") {
    const record = source as Record<string, unknown>;
    for (const key of keys) {
      const value = record[key];
      if (typeof value === "number") {
        return value;
      }
      if (typeof value === "string" && value.trim() !== "") {
        const parsed = Number(value);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
    }
  }
  return fallback;
}

export function pickText(source: unknown, keys: string[], fallback = "-") {
  if (source && typeof source === "object") {
    const record = source as Record<string, unknown>;
    for (const key of keys) {
      const value = record[key];
      if (value !== undefined && value !== null && String(value) !== "") {
        return String(value);
      }
    }
  }
  return fallback;
}

export function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

export function monthStartIsoDate() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .slice(0, 10);
}
