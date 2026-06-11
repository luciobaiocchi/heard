// ── Constants ─────────────────────────────────────────────────────
export const TERRAIN_EXAG = 1.3;
export const LINK_FADE_S = 5.0;       // sim-seconds a link arc stays visible
export const TRAIL_S = 60.0;          // sim-seconds of path trail per device
export const WAVE_DURATION_S = 4.0;   // sim-seconds a radio wave ring takes to expand to R_MAX
export const LOG_MAX = 120;

// ── Colour palette ────────────────────────────────────────────────
export const CLR = {
  path: "#53d8fb",
  core: "#e94560",
  node: "#58a6ff",
  out: "#f85149",
  safezone: "#7ee787",
  REQ: "#f5a623",
  WAIT: "#58a6ff",
  POS: "#7ee787",
  drop: "#555566",
};

// Pre-computed unit circle (cos/sin table) — avoids trig per circle at render time
export const CIRCLE_STEPS = 40;
const _unitCircle = Array.from({ length: CIRCLE_STEPS + 1 }, (_, i) => {
  const a = (i / CIRCLE_STEPS) * 2 * Math.PI;
  return [Math.cos(a), Math.sin(a)]; // [latDir, lonDir]
});
export const UNIT_CIRCLE = _unitCircle;
