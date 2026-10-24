/** Round half up for display (82.5 -> 83), matching the engine. Math.round alone drifts on 1.005-style floats. */
export function rhu(x: number, digits = 0): number {
  return Number(`${Math.round(Number(`${x}e${digits}`))}e-${digits}`);
}

export function pct(x: number | null | undefined, digits = 1): string {
  return x === null || x === undefined ? "—" : `${rhu(x, digits)}%`;
}

export function num(x: number | null | undefined, digits = 2): string {
  return x === null || x === undefined ? "—" : String(rhu(x, digits));
}

/** "supplier" -> "Supplier", "jv_partner" -> "Jv partner"; prefer config labels where they exist. */
export function humanize(code: string): string {
  const s = code.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** "tamil_nadu" -> "Tamil Nadu": every word capitalised, for place names. */
export function placeName(code: string): string {
  return code.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}
