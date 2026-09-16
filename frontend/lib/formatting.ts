export function formatNumber(n: number | undefined | null): string {
  if (n === undefined || n === null || isNaN(n)) return "—";
  return n.toLocaleString("en-US");
}

export function formatMetric(n: number | undefined | null, decimals: number = 4): string {
  if (n === undefined || n === null || isNaN(n)) return "—";
  return n.toFixed(decimals);
}

export function formatCompactTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return dateStr;
  }
}
