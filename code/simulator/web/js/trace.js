// Loads trace.json and returns all derived constants/helpers, or null on failure.
export async function loadTrace() {
  let trace;
  try {
    const resp = await fetch("trace.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    trace = await resp.json();
  } catch {
    document.body.innerHTML = `
      <div style="color:#f85149;padding:40px;font-family:monospace;background:#0d1117;min-height:100vh">
        <b>Could not load trace.json</b><br><br>
        Run: <code>python3 record.py</code><br>
        Then: <code>cd web &amp;&amp; python3 -m http.server 8000</code>
      </div>`;
    return null;
  }

  const { meta, path: trail, frames, margin_left, margin_right } = trace;
  const TICK_S = meta.tick_s;
  const N_TICKS = meta.num_ticks;
  const R_REL = meta.lora_reliable_m;
  const R_MAX = meta.lora_max_m;
  const FRAME_STRIDE = meta.frame_stride ?? 1;

  // O(1) frame lookup — frames[i].tick == i * FRAME_STRIDE
  function frameAt(tick) {
    const idx = Math.min(
      frames.length - 1,
      Math.max(0, Math.floor(tick / FRAME_STRIDE)),
    );
    return frames[idx];
  }
  function frameRange(minTick, maxTick) {
    const lo = Math.max(0, Math.ceil(minTick / FRAME_STRIDE));
    const hi = Math.min(frames.length - 1, Math.floor(maxTick / FRAME_STRIDE));
    return { lo, hi };
  }

  const deviceRole = {};
  meta.devices.forEach((d) => {
    deviceRole[d.id] = d.role;
  });
  const coreMeta = meta.devices.find((d) => d.role === "core");

  return {
    meta,
    trail,
    frames,
    margin_left,
    margin_right,
    TICK_S,
    N_TICKS,
    R_REL,
    R_MAX,
    FRAME_STRIDE,
    frameAt,
    frameRange,
    deviceRole,
    coreMeta,
  };
}
