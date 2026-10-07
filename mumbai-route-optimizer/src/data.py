from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_locations(path=None):
    """Read locations.csv. Row 0 is always the depot."""
    path = Path(path) if path else DATA_DIR / "locations.csv"
    df = pd.read_csv(path)
    if not df.loc[0, "name"].lower().startswith("depot"):
        raise ValueError("first row of the csv must be the depot")
    return df
