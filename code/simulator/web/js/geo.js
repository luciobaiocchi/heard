import { UNIT_CIRCLE } from "./constants.js";

export function circleFeature(lat, lon, radius_m, props = {}) {
  const R = 6_371_000;
  const dlatPerM = 180 / (Math.PI * R);
  const dlonPerM = 180 / (Math.PI * R * Math.cos((lat * Math.PI) / 180));
  const dlat = radius_m * dlatPerM;
  const dlon = radius_m * dlonPerM;
  const coords = UNIT_CIRCLE.map(([c, s]) => [lon + s * dlon, lat + c * dlat]);
  return {
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [coords] },
    properties: props,
  };
}

// Per-wave-origin scale factors (precomputed once at load time, no trig per frame).
// Deduplication key is (src, evTick) so each broadcast event gets exactly one ring,
// even when multiple recipients appear in the same link list.
// lk.tick (added in record.py) carries the actual sim tick of the event so that
// relay waves (which happen 1 tick after the core broadcast) get their own timing.
export function buildWaveEvents(frames) {
  return frames.map((f) => {
    const seen = new Set(); // 'srcId:evTick'
    const waves = [];
    for (const lk of f.links) {
      if (!lk.ok) continue;
      const evTick = lk.tick ?? f.tick;
      const key = `${lk.src}:${evTick}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const src = f.devices.find((x) => x.id === lk.src);
      if (src) {
        const R = 6_371_000;
        waves.push({
          lat: src.lat,
          lon: src.lon,
          kind: lk.kind,
          tick: evTick,
          dlatPerM: 180 / (Math.PI * R),
          dlonPerM: 180 / (Math.PI * R * Math.cos((src.lat * Math.PI) / 180)),
        });
      }
    }
    return waves;
  });
}
