import { CLR, TRAIL_S, WAVE_DURATION_S, LINK_FADE_S, UNIT_CIRCLE } from "./constants.js";
import { circleFeature } from "./geo.js";

export function createRenderer(map, trace, waveEvents) {
  const { meta, frames, TICK_S, R_REL, R_MAX, frameRange, coreMeta } = trace;

  // Caches to skip redundant setData() calls
  let cachedCoreKey = "";  // 'lat,lon' rounded to ~10 m
  let cachedTrailKey = ""; // 'tLo-tHi'

  function renderDynamic(t, frame, speed = 5) {
    // Range circles — only rebuild when core has moved ≥ ~10 m
    const coreDev = frame.devices.find((ds) => ds.id === coreMeta.id);
    if (coreDev) {
      const coreKey = `${coreDev.lat.toFixed(4)},${coreDev.lon.toFixed(4)}`;
      if (coreKey !== cachedCoreKey) {
        cachedCoreKey = coreKey;
        map.getSource("range-circles").setData({
          type: "FeatureCollection",
          features: [
            circleFeature(coreDev.lat, coreDev.lon, R_MAX, { ring: "max" }),
            circleFeature(coreDev.lat, coreDev.lon, R_REL, {
              ring: "reliable",
            }),
          ],
        });
      }
    }

    // Device trails — only rebuild when the frame window changes
    const { lo: tLo, hi: tHi } = frameRange(t - TRAIL_S / TICK_S, t);
    const trailKey = `${tLo}-${tHi}`;
    if (trailKey !== cachedTrailKey) {
      cachedTrailKey = trailKey;
      const trailBuf = {};
      meta.devices.forEach((d) => {
        trailBuf[d.id] = [];
      });
      for (let i = tLo; i <= tHi; i++) {
        frames[i].devices.forEach((ds) => {
          trailBuf[ds.id].push([ds.lon, ds.lat]);
        });
      }
      map.getSource("device-trails").setData({
        type: "FeatureCollection",
        features: meta.devices
          .filter((d) => trailBuf[d.id].length > 1)
          .map((d) => ({
            type: "Feature",
            geometry: { type: "LineString", coordinates: trailBuf[d.id] },
            properties: {
              color: d.role === "core" ? CLR.core : CLR.node,
              role: d.role,
            },
          })),
      });
    }

    // Radio wave rings — each wave uses its own event tick for accurate age/timing.
    // This ensures relay waves (1 tick after the broadcast) expand independently.
    // Duration scales with playback speed so rings stay visible at 50×/100×
    // (a fixed sim-time duration would flash for a few milliseconds of real time).
    const waveTicks = (WAVE_DURATION_S * Math.max(1, speed / 5)) / TICK_S;
    const { lo: wLo, hi: wHi } = frameRange(t - waveTicks, t);
    const waveFeatures = [];
    for (let i = wLo; i <= wHi; i++) {
      for (const w of waveEvents[i]) {
        const age = t - w.tick;
        if (age < 0 || age > waveTicks) continue;
        const progress = age / waveTicks;
        const radius_m = progress * R_MAX;
        if (radius_m < 50) continue;
        const opacity = (1 - progress) * 0.18;
        const dlat = radius_m * w.dlatPerM;
        const dlon = radius_m * w.dlonPerM;
        const coords = UNIT_CIRCLE.map(([c, s]) => [
          w.lon + s * dlon,
          w.lat + c * dlat,
        ]);
        waveFeatures.push({
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [coords] },
          properties: { kind: w.kind, opacity },
        });
      }
    }
    map
      .getSource("radio-waves")
      .setData({ type: "FeatureCollection", features: waveFeatures });

    // Link arcs (fade over LINK_FADE_S)
    const linkFadeTicks = LINK_FADE_S / TICK_S;
    const { lo: lLo, hi: lHi } = frameRange(t - linkFadeTicks, t);
    const linkFeatures = [];
    for (let i = lHi; i >= lLo; i--) {
      const f = frames[i];
      const age = t - f.tick;
      const alpha = Math.max(0, 1 - age / linkFadeTicks);
      for (const lk of f.links) {
        const src = f.devices.find((x) => x.id === lk.src);
        if (!src) continue;
        const targets =
          lk.dst === -1
            ? f.devices.filter((x) => x.id !== lk.src)
            : f.devices.filter((x) => x.id === lk.dst);
        for (const dst of targets) {
          linkFeatures.push({
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: [
                [src.lon, src.lat],
                [dst.lon, dst.lat],
              ],
            },
            properties: {
              kind: lk.kind,
              ok: lk.ok,
              alpha: alpha * (lk.ok ? 0.9 : 0.3),
            },
          });
        }
      }
    }
    map
      .getSource("links")
      .setData({ type: "FeatureCollection", features: linkFeatures });
  }

  return { renderDynamic };
}
