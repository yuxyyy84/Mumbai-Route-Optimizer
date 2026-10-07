import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf"]


def _draw_points(ax, df):
    ax.scatter(df["lng"][1:], df["lat"][1:], s=22, color="#555555", zorder=3)
    ax.scatter(df["lng"][0], df["lat"][0], s=140, marker="*", color="black", zorder=4, label="Depot")
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_aspect(1.0 / 0.95)   # roughly correct shape at Mumbai's latitude


def plot_tour(df, tour, title, path):
    fig, ax = plt.subplots(figsize=(6, 8))
    xs = [df["lng"][i] for i in tour] + [df["lng"][tour[0]]]
    ys = [df["lat"][i] for i in tour] + [df["lat"][tour[0]]]
    ax.plot(xs, ys, color="#1f77b4", linewidth=1.4, zorder=2)
    _draw_points(ax, df)
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_routes(df, routes, title, path):
    fig, ax = plt.subplots(figsize=(6, 8))
    for k, r in enumerate(routes):
        pts = [0] + list(r) + [0]
        ax.plot([df["lng"][i] for i in pts], [df["lat"][i] for i in pts],
                color=COLORS[k % len(COLORS)], linewidth=1.5, label=f"Vehicle {k + 1}", zorder=2)
    _draw_points(ax, df)
    ax.set_title(title)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_convergence(history, baseline_nn, baseline_2opt, path):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(history, color="#1f77b4", label="Genetic algorithm (best of generation)")
    ax.axhline(baseline_nn, color="#d62728", linestyle="--", label="Nearest neighbour")
    ax.axhline(baseline_2opt, color="#2ca02c", linestyle="--", label="Nearest neighbour + 2-opt")
    ax.set_xlabel("generation")
    ax.set_ylabel("tour length (km)")
    ax.set_title("GA convergence")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_bar(names, values, title, path):
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, values, color="#4c72b0")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("total distance (km)")
    ax.set_title(title)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# Interactive map. Plain Leaflet + OpenStreetMap tiles, so it needs internet when
# you open the file, but no extra python package. Lines are straight segments
# between stops, not the actual road geometry.
_MAP_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map { height: 100%; margin: 0; }
  .title { position: absolute; z-index: 1000; top: 10px; left: 55px; background: white;
           padding: 6px 12px; border-radius: 4px; font: 14px sans-serif; box-shadow: 0 1px 4px #0006; }
</style>
</head>
<body>
<div class="title">__TITLE__</div>
<div id="map"></div>
<script>
const stops = __STOPS__;
const routes = __ROUTES__;
const colors = __COLORS__;

const map = L.map('map').setView([19.08, 72.87], 11);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

routes.forEach((r, k) => {
  const pts = r.map(i => [stops[i].lat, stops[i].lng]);
  L.polyline(pts, {color: colors[k % colors.length], weight: 4, opacity: 0.8})
    .bindTooltip('Vehicle ' + (k + 1)).addTo(map);
});

stops.forEach((s, i) => {
  const isDepot = i === 0;
  L.circleMarker([s.lat, s.lng], {
    radius: isDepot ? 9 : 5, color: isDepot ? 'black' : '#333',
    fillColor: isDepot ? 'gold' : 'white', fillOpacity: 1, weight: 2
  }).bindPopup('<b>' + s.name + '</b><br>' + s.area + (isDepot ? '' : '<br>parcels: ' + s.parcels)).addTo(map);
});
</script>
</body>
</html>
"""


def write_map(df, routes, title, path):
    """routes: list of node-id lists. Each one is drawn as depot -> stops -> depot."""
    stops = [dict(name=r["name"], area=r["area"], lat=float(r["lat"]), lng=float(r["lng"]),
                  parcels=int(r["parcels"])) for _, r in df.iterrows()]
    full = [[0] + [int(x) for x in r if x != 0] + [0] for r in routes]
    html = (_MAP_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__STOPS__", json.dumps(stops))
            .replace("__ROUTES__", json.dumps(full))
            .replace("__COLORS__", json.dumps(COLORS)))
    Path(path).write_text(html, encoding="utf-8")
