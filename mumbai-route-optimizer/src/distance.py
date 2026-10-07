import json
from pathlib import Path

import numpy as np

EARTH_RADIUS_KM = 6371.0088

# Roads in Mumbai are never a straight line between two places. I use 1.35 as a
# rough detour factor on top of the straight-line distance. This is an
# assumption, not a measured number - see README. If you have road distances
# from OSRM (scripts/fetch_road_distances.py) they are used instead.
DETOUR_FACTOR = 1.35


def haversine_matrix(lats, lngs):
    """Straight-line (great circle) distance between every pair of points, in km."""
    lat = np.radians(np.asarray(lats, dtype=float))
    lng = np.radians(np.asarray(lngs, dtype=float))
    dlat = lat[:, None] - lat[None, :]
    dlng = lng[:, None] - lng[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def build_matrix(df, road_file=None):
    """Return (distance matrix in km, short text describing where it came from)."""
    if road_file and Path(road_file).exists():
        with open(road_file) as f:
            saved = json.load(f)
        mat = np.array(saved["distances_km"], dtype=float)
        if mat.shape == (len(df), len(df)):
            return mat, "OSRM road distances"
        print("road matrix size does not match locations.csv, ignoring it")

    mat = haversine_matrix(df["lat"], df["lng"]) * DETOUR_FACTOR
    return mat, f"haversine x {DETOUR_FACTOR} detour factor"
