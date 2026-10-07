"""Optional: replace the straight-line estimate with real road distances.

Asks the public OSRM demo server for a driving distance table between all the
locations in data/locations.csv and saves it as data/road_matrix.json.
run.py picks that file up automatically.

Needs internet. The demo server is meant for light use - run this once, not in a loop.
Road distances can differ by direction (one-way streets), the solvers here assume
symmetric distances, so the matrix is averaged with its transpose.
"""
import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import load_locations  # noqa: E402

OSRM_URL = "https://router.project-osrm.org/table/v1/driving/"


def main():
    df = load_locations()
    coords = ";".join(f"{lng},{lat}" for lat, lng in zip(df["lat"], df["lng"]))
    resp = requests.get(OSRM_URL + coords, params={"annotations": "distance"}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        sys.exit(f"OSRM said: {data.get('code')} {data.get('message', '')}")

    meters = np.array(data["distances"], dtype=float)
    if np.isnan(meters).any():
        sys.exit("some pairs had no route - check the coordinates in locations.csv")

    km = meters / 1000.0
    km = (km + km.T) / 2
    out = ROOT / "data" / "road_matrix.json"
    out.write_text(json.dumps({"source": "OSRM", "distances_km": km.round(3).tolist()}))
    print(f"saved {out}  ({km.shape[0]} x {km.shape[1]})")


if __name__ == "__main__":
    main()
