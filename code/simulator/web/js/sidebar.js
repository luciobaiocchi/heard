import { LOG_MAX } from "./constants.js";

export function createSidebar(meta) {
  // ── Sidebar panel elements ────────────────────────────────────
  const elModeChip   = document.getElementById("mode-chip");
  const elReqBadge   = document.getElementById("req-badge");
  const elKnownBody  = document.getElementById("known-body");
  const elOutBadge   = document.getElementById("out-badge");
  const elSent       = document.getElementById("m-sent");
  const elDelivered  = document.getElementById("m-delivered");
  const elDropped    = document.getElementById("m-dropped");
  const elRate       = document.getElementById("m-rate");
  const elLog        = document.getElementById("log-body");
  const elSparkline  = document.getElementById("sparkline");
  const sparkCtx     = elSparkline.getContext("2d");
  const elReachHead  = document.getElementById("reach-head");
  const elReachRows  = document.getElementById("reach-rows");

  if (elModeChip) elModeChip.textContent = meta.mode ?? "uniform";

  // Connectivity table skeleton (built once, cells updated in-place)
  const reachCells = {};
  (() => {
    const hth = document.createElement("th");
    hth.textContent = "hears ↓\\";
    hth.style.textAlign = "left";
    elReachHead.appendChild(hth);
    meta.devices.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.role === "core" ? "★" : col.id;
      elReachHead.appendChild(th);
    });
    meta.devices.forEach((row) => {
      const tr = document.createElement("tr");
      const td0 = document.createElement("td");
      td0.className = "reach-label";
      td0.textContent = row.role === "core" ? "★C" : `N${row.id}`;
      tr.appendChild(td0);
      reachCells[row.id] = {};
      meta.devices.forEach((col) => {
        const td = document.createElement("td");
        td.className = row.id === col.id ? "reach-self" : "reach-no";
        td.textContent = row.id === col.id ? "·" : "—";
        tr.appendChild(td);
        reachCells[row.id][col.id] = td;
      });
      elReachRows.appendChild(tr);
    });
  })();

  const rateHistory = [];
  const prevOutIds = new Set();
  let lastPanelTick = -1;

  function drawSparkline() {
    const w = elSparkline.width,
      h = elSparkline.height;
    sparkCtx.clearRect(0, 0, w, h);
    const pts = rateHistory.filter((r) => r !== null);
    if (pts.length < 2) return;
    sparkCtx.beginPath();
    sparkCtx.strokeStyle = "#3fb950";
    sparkCtx.lineWidth = 1.5;
    pts.forEach((p, i) => {
      const x = (i / (pts.length - 1)) * w;
      const y = h - p * h;
      i === 0 ? sparkCtx.moveTo(x, y) : sparkCtx.lineTo(x, y);
    });
    sparkCtx.stroke();
  }

  function update(frame) {
    // ── Sidebar panels (skip if recorded frame unchanged) ─────
    if (frame.tick === lastPanelTick) return;
    lastPanelTick = frame.tick;

    const st = frame.state;
    elReqBadge.textContent = st.req_active ? "ACTIVE" : "idle";
    elReqBadge.className = "badge " + (st.req_active ? "active" : "idle");
    elKnownBody.innerHTML = st.known
      .map(
        (k) =>
          `<tr><td>${k.id}</td><td>${k.lat.toFixed(4)}</td><td>${k.lon.toFixed(4)}</td></tr>`,
      )
      .join("");

    const nowOutIds = new Set(
      frame.devices
        .filter((d) => d.out && meta.devices.find((md) => md.id === d.id)?.role !== "core")
        .map((d) => d.id),
    );
    nowOutIds.forEach((id) => {
      if (!prevOutIds.has(id)) {
        const line = document.createElement("div");
        line.className = "log-out";
        line.textContent = `t${frame.tick} ⚠ Node ${id} OUT_PATH`;
        elLog.appendChild(line);
        elLog.scrollTop = elLog.scrollHeight;
      }
    });
    prevOutIds.clear();
    nowOutIds.forEach((id) => prevOutIds.add(id));

    if (elOutBadge) {
      const outList = [...nowOutIds];
      elOutBadge.textContent = outList.length
        ? outList.map((id) => `N${id}`).join(", ")
        : "none";
      elOutBadge.className = "badge " + (outList.length ? "out" : "idle");
    }

    frame.devices.forEach((d) => {
      const reachSet = new Set(d.reach ?? []);
      meta.devices.forEach((col) => {
        if (col.id === d.id) return;
        const td = reachCells[d.id]?.[col.id];
        if (!td) return;
        const ok = reachSet.has(col.id);
        td.textContent = ok ? "✓" : "—";
        td.className = ok ? "reach-ok" : "reach-no";
      });
    });

    const m = frame.metrics;
    elSent.textContent = m.sent;
    elDelivered.textContent = m.delivered;
    elDropped.textContent = m.dropped;
    elRate.textContent =
      m.sent > 0 ? ((100 * m.delivered) / m.sent).toFixed(1) + "%" : "—";
    rateHistory.push(m.sent > 0 ? m.delivered / m.sent : null);
    if (rateHistory.length > 200) rateHistory.shift();
    drawSparkline();

    if (frame.links.length) {
      const frag = document.createDocumentFragment();
      frame.links.forEach((lk) => {
        const line = document.createElement("div");
        line.className = lk.ok ? `log-${lk.kind.toLowerCase()}` : "log-fail";
        line.textContent = `t${frame.tick} ${lk.kind} ${lk.src}→${lk.dst === -1 ? "all" : lk.dst} ${lk.ok ? "✓" : "✗"}`;
        frag.appendChild(line);
      });
      elLog.appendChild(frag);
      while (elLog.childElementCount > LOG_MAX)
        elLog.removeChild(elLog.firstChild);
      elLog.scrollTop = elLog.scrollHeight;
    }
  }

  return { update };
}
