import { TERRAIN_EXAG } from "./constants.js";
import { MAPTILER_KEY, MAP_STYLE } from "./style.js";

export async function createMap(trail) {
  const lats = trail.map((p) => p[0]);
  const lons = trail.map((p) => p[1]);
  const bounds = [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ];

  const map = new maplibregl.Map({
    container: "map",
    style: MAP_STYLE,
    bounds,
    fitBoundsOptions: { padding: 80 },
    pitch: 55,
    bearing: -15,
    antialias: true,
    maxPitch: 85,
  });
  map.addControl(
    new maplibregl.NavigationControl({ visualizePitch: true }),
    "top-left",
  );

  await new Promise((r) => map.once("load", r));

  // ── Terrain & sky ────────────────────────────────────────────
  map.addSource("_dem", {
    type: "raster-dem",
    tiles: [
      "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
    ],
    tileSize: 256,
    encoding: "terrarium",
    maxzoom: 14,
  });
  map.setTerrain({ source: "_dem", exaggeration: TERRAIN_EXAG });

  if (!MAPTILER_KEY) {
    const firstSym = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
    map.addLayer(
      {
        id: "_hillshade",
        type: "hillshade",
        source: "_dem",
        paint: {
          "hillshade-exaggeration": 0.45,
          "hillshade-shadow-color": "#334",
          "hillshade-illumination-anchor": "viewport",
        },
      },
      firstSym,
    );
  }

  map.setSky({
    "sky-type": "atmosphere",
    "sky-atmosphere-sun": [0.0, 90.0],
    "sky-atmosphere-sun-intensity": 15,
  });

  return map;
}
