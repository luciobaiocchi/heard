export function createPlayback(map, { nTicks, tickS, render }) {
  let currentTick = 0;
  let isPlaying = false;
  let playSpeed = 5;
  let lastTimestamp = null;

  const btnPlay  = document.getElementById("btn-play");
  const slider   = document.getElementById("timeline");
  const tickDisp = document.getElementById("tick-display");
  const speedSel = document.getElementById("speed-select");
  slider.max = nTicks - 1;

  btnPlay.addEventListener("click", () => {
    isPlaying = !isPlaying;
    btnPlay.textContent = isPlaying ? "⏸" : "▶";
    if (!isPlaying) lastTimestamp = null;
  });
  slider.addEventListener("input", () => {
    currentTick = Number(slider.value);
  });
  speedSel.addEventListener("change", () => {
    playSpeed = Number(speedSel.value);
  });

  let lastRenderedTick = -1;
  // Re-render when terrain tiles stream in so marker altitudes correct themselves
  // from the approximate GPX fallback to the precise DEM value.
  let terrainTilesChanged = false;
  map.on("data", (e) => { if (e.tile) terrainTilesChanged = true; });

  function loop(ts) {
    requestAnimationFrame(loop);
    if (isPlaying) {
      if (lastTimestamp !== null) {
        currentTick =
          (currentTick + (((ts - lastTimestamp) / 1000) * playSpeed) / tickS) %
          nTicks;
      }
      lastTimestamp = ts;
    }
    // Skip render when paused, tick unchanged, and no new terrain tiles
    const tickInt = currentTick | 0;
    if (!isPlaying && tickInt === lastRenderedTick && !terrainTilesChanged) return;
    terrainTilesChanged = false;
    lastRenderedTick = tickInt;

    slider.value = tickInt;
    tickDisp.textContent = `t ${tickInt}  (${(tickInt * tickS).toFixed(0)} s)`;

    render(currentTick);
  }
  requestAnimationFrame(loop);

  return {
    getTick() { return currentTick; },
    getSpeed() { return playSpeed; },
  };
}
