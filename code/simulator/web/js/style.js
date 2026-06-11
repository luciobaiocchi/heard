// ── Map style ─────────────────────────────────────────────────────
export const MAPTILER_KEY = window.MAPTILER_KEY ?? null;
const MAP_STYLE_KEY = window.MAP_STYLE_KEY ?? "outdoor";

// Free fallback styles (no API key needed)
const FREE_STYLES = {
  outdoor: "https://tiles.openfreemap.org/styles/liberty",
  satellite: {
    version: 8,
    glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
    sources: {
      esri: {
        type: "raster",
        tileSize: 256,
        attribution: "© Esri",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
      },
      esri_labels: {
        type: "raster",
        tileSize: 256,
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        ],
      },
    },
    layers: [
      { id: "esri-sat", type: "raster", source: "esri" },
      { id: "esri-labels", type: "raster", source: "esri_labels" },
    ],
  },
  topo: "https://tiles.openfreemap.org/styles/positron",
};

// MapTiler styles (require a free API key in config.js → window.MAPTILER_KEY)
const MAPTILER_STYLES = {
  outdoor: "outdoor-v2",
  satellite: "satellite",
  hybrid: "hybrid",
  topo: "topo-v2",
};

export const MAP_STYLE = MAPTILER_KEY
  ? `https://api.maptiler.com/maps/${MAPTILER_STYLES[MAP_STYLE_KEY] ?? MAP_STYLE_KEY}/style.json?key=${MAPTILER_KEY}`
  : (FREE_STYLES[MAP_STYLE_KEY] ?? FREE_STYLES.outdoor);
