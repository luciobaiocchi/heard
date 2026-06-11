/* ════════════════════════════════════════════════════════════════
   HEARD — MapLibre GL JS 3D simulation replay
   record.py → trace.json → this viewer
   ════════════════════════════════════════════════════════════════ */

import { loadTrace }        from "./js/trace.js";
import { createMap }        from "./js/map-setup.js";
import { addStaticLayers, addDynamicLayers } from "./js/layers.js";
import { addDeviceLayers, updateDevices }    from "./js/markers.js";
import { createSidebar }    from "./js/sidebar.js";
import { createRenderer }   from "./js/render.js";
import { createDebugOverlay } from "./js/debug.js";
import { createPlayback }   from "./js/playback.js";
import { buildWaveEvents }  from "./js/geo.js";

async function main() {
  const trace = await loadTrace();
  if (!trace) return;

  const { meta, trail, frames, N_TICKS, TICK_S } = trace;

  const map = await createMap(trail);

  addStaticLayers(map, trace);
  addDynamicLayers(map);
  addDeviceLayers(map);

  const sidebar    = createSidebar(meta);
  const waveEvents = buildWaveEvents(frames);
  const renderer   = createRenderer(map, trace, waveEvents);
  const debug      = createDebugOverlay(
    () => playback.getTick(),
    () => trace.frameAt(playback.getTick()),
  );

  function render(t) {
    const frame = trace.frameAt(t);
    updateDevices(map, trace, t);
    renderer.renderDynamic(t, frame, playback.getSpeed());
    sidebar.update(frame);
    debug.refresh();
  }

  const playback = createPlayback(map, {
    nTicks: N_TICKS,
    tickS:  TICK_S,
    render,
  });

  console.log(
    `HEARD: ${N_TICKS} ticks · ${meta.devices.length} devices · mode: ${meta.mode ?? "uniform"}`,
  );
}

main();
