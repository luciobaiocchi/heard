import { TERRAIN_EXAG } from "./constants.js";

export function createDebugOverlay(getTick, getFrame) {
  const _dbgPanel = document.createElement("div");
  _dbgPanel.id = "dbg-panel";
  _dbgPanel.style.cssText = [
    "position:fixed", "bottom:8px", "left:8px", "z-index:9999",
    "background:rgba(0,0,0,0.82)", "color:#7ee787", "font:11px/1.5 monospace",
    "padding:8px 10px", "border-radius:6px", "pointer-events:none",
    "display:none", "white-space:pre",
  ].join(";");
  document.body.appendChild(_dbgPanel);

  function refresh() {
    if (_dbgPanel.style.display === "none") return;
    const lines = [`TERRAIN_EXAG=${TERRAIN_EXAG}  tick=${getTick() | 0}`];
    for (const ds of getFrame().devices) {
      lines.push(
        `id=${ds.id}  gpsEle=${ds.ele?.toFixed(0) ?? "?"}m  demEle=${(ds.dem_ele ?? 0).toFixed(0)}m`
      );
    }
    _dbgPanel.textContent = lines.join("\n");
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "d" || e.key === "D") {
      _dbgPanel.style.display = _dbgPanel.style.display === "none" ? "block" : "none";
    }
  });

  return { refresh };
}
