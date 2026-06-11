import { CLR } from "./constants.js";

export function addStaticLayers(map, trace) {
  const { trail, margin_left, margin_right } = trace;

  // ── Static layers: GPX trail ──────────────────────────────────
  const trailCoords = trail.map(([lat, lon]) => [lon, lat]);
  map.addSource("trail", {
    type: "geojson",
    data: {
      type: "Feature",
      geometry: { type: "LineString", coordinates: trailCoords },
      properties: {},
    },
  });
  map.addLayer({
    id: "trail-shadow",
    type: "line",
    source: "trail",
    paint: {
      "line-color": "#000",
      "line-width": 7,
      "line-opacity": 0.2,
      "line-blur": 4,
    },
  });
  map.addLayer({
    id: "trail-line",
    type: "line",
    source: "trail",
    paint: { "line-color": CLR.path, "line-width": 3, "line-opacity": 0.9 },
  });

  // ── Static layers: safe-zone corridor ────────────────────────
  if (margin_left?.length > 1 && margin_right?.length > 1) {
    const mlC = margin_left.map(([lat, lon]) => [lon, lat]);
    const mrC = margin_right.map(([lat, lon]) => [lon, lat]);

    // Closed polygon ring: left edge → reversed right edge → back to start
    const ring = [...mlC, ...[...mrC].reverse(), mlC[0]];

    map.addSource("corridor", {
      type: "geojson",
      data: {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [ring] },
        properties: {},
      },
    });
    map.addLayer({
      id: "corridor-fill",
      type: "fill",
      source: "corridor",
      paint: { "fill-color": CLR.safezone, "fill-opacity": 0.13 },
    });

    map.addSource("margin-lines", {
      type: "geojson",
      data: {
        type: "Feature",
        geometry: { type: "MultiLineString", coordinates: [mlC, mrC] },
        properties: {},
      },
    });
    map.addLayer({
      id: "margin-lines-layer",
      type: "line",
      source: "margin-lines",
      paint: {
        "line-color": CLR.safezone,
        "line-width": 2,
        "line-opacity": 0.65,
        "line-dasharray": [6, 4],
      },
    });
  }
}

export function addDynamicLayers(map) {
  const emptyFC = () => ({ type: "FeatureCollection", features: [] });

  for (const id of ["device-trails", "radio-waves", "links", "range-circles"]) {
    map.addSource(id, { type: "geojson", data: emptyFC() });
  }

  // Device path trails
  map.addLayer({
    id: "device-trails-line",
    type: "line",
    source: "device-trails",
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["case", ["==", ["get", "role"], "core"], 3, 2],
      "line-opacity": 0.55,
    },
  });

  // Radio wave rings — expanding circles from each transmitting device
  map.addLayer({
    id: "radio-waves-fill",
    type: "fill",
    source: "radio-waves",
    paint: {
      "fill-color": [
        "case",
        ["==", ["get", "kind"], "REQ"],
        CLR.REQ,
        ["==", ["get", "kind"], "WAIT"],
        CLR.WAIT,
        ["==", ["get", "kind"], "POS"],
        CLR.POS,
        "#fff",
      ],
      "fill-opacity": ["get", "opacity"],
    },
  });
  map.addLayer({
    id: "radio-waves-outline",
    type: "line",
    source: "radio-waves",
    paint: {
      "line-color": [
        "case",
        ["==", ["get", "kind"], "REQ"],
        CLR.REQ,
        ["==", ["get", "kind"], "WAIT"],
        CLR.WAIT,
        ["==", ["get", "kind"], "POS"],
        CLR.POS,
        "#fff",
      ],
      "line-width": 1.5,
      "line-opacity": ["min", 1, ["*", 3.0, ["get", "opacity"]]],
    },
  });

  // LoRa link arcs
  map.addLayer({
    id: "links-line",
    type: "line",
    source: "links",
    paint: {
      "line-color": [
        "case",
        ["!", ["get", "ok"]],
        CLR.drop,
        ["==", ["get", "kind"], "REQ"],
        CLR.REQ,
        ["==", ["get", "kind"], "WAIT"],
        CLR.WAIT,
        ["==", ["get", "kind"], "POS"],
        CLR.POS,
        "#fff",
      ],
      "line-width": ["case", ["get", "ok"], 2, 1],
      "line-opacity": ["get", "alpha"],
    },
  });

  // Range circles around core (reliable + max)
  map.addLayer({
    id: "range-max-fill",
    type: "fill",
    source: "range-circles",
    filter: ["==", ["get", "ring"], "max"],
    paint: { "fill-color": "#fff", "fill-opacity": 0.03 },
  });
  map.addLayer({
    id: "range-rel-fill",
    type: "fill",
    source: "range-circles",
    filter: ["==", ["get", "ring"], "reliable"],
    paint: { "fill-color": "#fff", "fill-opacity": 0.07 },
  });
  map.addLayer({
    id: "range-rel-outline",
    type: "line",
    source: "range-circles",
    filter: ["==", ["get", "ring"], "reliable"],
    paint: { "line-color": "#fff", "line-width": 1, "line-opacity": 0.25 },
  });
}
