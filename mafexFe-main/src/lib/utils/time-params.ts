/** Normalize HTML `time` input (HH:MM) for API query params (HH:MM:SS). */
export function normalizeTimeParam(t: string | undefined): string | undefined {
  const trimmed = t?.trim();
  if (!trimmed) return undefined;
  if (trimmed.length === 5) return `${trimmed}:00`;
  return trimmed;
}

export function isValidTimeRange(start: string, end: string): boolean {
  if (!start || !end) return false;
  return start < end;
}
