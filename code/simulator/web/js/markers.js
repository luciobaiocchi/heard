// Devices are rendered as native map layers (circle dots + symbol labels) so the
// GPU positions them with the same DEM as the terrain — they can never float
// relative to the surface, unlike DOM markers whose CPU-side elevation queries
// diverge from the rendered terrain (e.g. past the DEM source's maxzoom).
import { CLR } from "./constants.js";

export function addDeviceLayers(map) {
  map.addSource("devices", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });

  map.addLayer({
    id: "device-dots",
    type: "circle",
    source: "devices",
    paint: {
      "circle-radius": ["case", ["==", ["get", "role"], "core"], 8, 6],
      "circle-color": [
        "case",
        ["get", "out"],
        CLR.out,
        ["==", ["get", "role"], "core"],
        CLR.core,
        CLR.node,
      ],
      "circle-stroke-color": "rgba(255,255,255,0.9)",
      "circle-stroke-width": 2,
    },
  });

  map.addLayer({
    id: "device-labels",
    type: "symbol",
    source: "devices",
    layout: {
      "text-field": ["get", "label"],
      "text-font": ["Noto Sans Bold"],
      "text-size": 12,
      "text-anchor": "bottom",
      "text-offset": [0, -1.1],
      "text-allow-overlap": true,
      "text-ignore-placement": true,
    },
    paint: {
      "text-color": ["case", ["get", "out"], CLR.out, "#ffffff"],
      "text-halo-color": "#000000",
      "text-halo-width": 1.4,
    },
  });
}

// Positions are linearly interpolated between the recorded frame and the next
// one so motion stays smooth at any playback speed.
export function updateDevices(map, trace, t) {
  const frame = trace.frameAt(t);
  const next = trace.frameAt(frame.tick + trace.FRAME_STRIDE);
  const frac = Math.min(
    1,
    Math.max(0, (t - frame.tick) / trace.FRAME_STRIDE),
  );

  const features = frame.devices.map((ds) => {
    const nd =
      next !== frame ? next.devices.find((x) => x.id === ds.id) : null;
    const lon = nd ? ds.lon + (nd.lon - ds.lon) * frac : ds.lon;
    const lat = nd ? ds.lat + (nd.lat - ds.lat) * frac : ds.lat;
    const isCore = trace.deviceRole[ds.id] === "core";
    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        role: isCore ? "core" : "node",
        out: !!ds.out,
        label: (isCore ? "★ Core" : "N" + ds.id) + (ds.out ? " ⚠" : ""),
      },
    };
  });

  map.getSource("devices").setData({
    type: "FeatureCollection",
    features,
  });
}
