/** API time (`HH:MM` or `HH:MM:SS`) → HTML `time` input value. */
export function apiTimeToInput(value: string | undefined, fallback = "08:00"): string {
  if (!value) return fallback;
  return value.slice(0, 5);
}

/** HTML `time` input → API time with seconds. */
export function inputTimeToApi(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length === 5) return `${trimmed}:00`;
  return trimmed;
}
