# Mumbai Delivery Route Optimizer

Route optimization for a delivery depot in Kurla, Mumbai serving 45 real locations across the city
(Colaba in the south up to Borivali in the north, Mulund and Powai in the east).
The project compares a few classic optimization methods on two problems:

1. **TSP** - one vehicle has to visit all 45 stops and come back to the depot.
2. **CVRP** - 4 vehicles with a capacity of 75 parcels each have to cover all stops.

Everything is plain Python (numpy, pandas, matplotlib). Google OR-Tools is optional and is added to
the comparison automatically if it is installed.

## Results

Distances use the straight-line x 1.35 estimate described under "Data" below, so the kilometre
numbers are estimates, not driven distances.

**Part 1 - TSP (45 stops + depot)**

| Method | Distance (km) | Better than random | Runtime |
|---|---|---|---|
| Random order (average of 500) | 715.6 | - | - |
| Nearest neighbour | 190.6 | 73.4% | <0.01 s |
| Nearest neighbour + 2-opt | 150.7 | 78.9% | <0.01 s |
| Genetic algorithm | 148.8 | 79.2% | ~10 s |

2-opt gets most of the gain almost instantly. The genetic algorithm ends up only slightly better
(about 1.3%) but takes far longer, so for a problem this size a local search is the better deal.

**Part 2 - CVRP (4 vehicles, capacity 75)**

| Method | Distance (km) | Better than greedy |
|---|---|---|
| Greedy capacity-aware nearest neighbour | 276.6 | - |
| Greedy + 2-opt + relocate | 240.4 | 13.1% |
| Sweep + 2-opt + relocate | 210.3 | 24.0% |

The sweep start (sort stops by angle around the depot) gives much cleaner, non-overlapping routes than
the greedy start, and local search afterwards improves both. Plots are in `results/`
(`vrp_best.png`, `tsp_best_tour.png`, `ga_convergence.png`), and `results/*_map.html` are interactive maps.

These numbers come from `python run.py --no-ortools` with seed 42. Run it without that flag after
`pip install ortools` to get the OR-Tools rows as well.

A written analysis of all results (TSP, CVRP, Monte Carlo simulation and fleet-size what-if) is in
`REPORT.md` and, as a PDF with LaTeX source, in `report/report.pdf` and `report/report.tex`.

## Data

- **Locations**: `data/locations.csv` - 45 real places in Mumbai (railway stations, landmarks, business
  areas) plus a depot in Kurla. The coordinates are approximate (roughly within a few hundred metres),
  entered by hand. The depot is a hypothetical warehouse, not a real facility.
- **Parcels per stop**: simulated, random integers from 1 to 10 with a fixed seed. There is no real
  order data behind this.
- **Distances**: haversine (great-circle) distance multiplied by a detour factor of 1.35 to roughly
  account for roads. 1.35 is an assumption, not a measured value.
- **Real road distances (optional)**: `python scripts/fetch_road_distances.py` downloads a driving distance
  table from the public OSRM server and saves `data/road_matrix.json`. `run.py` uses it automatically
  when it exists. It needs internet access.

## How to run

```
pip install -r requirements.txt
python run.py
```

Options:

```
python run.py --vehicles 5 --capacity 60     # different fleet
python run.py --generations 2000 --seed 7    # GA settings
python run.py --no-ortools                   # skip OR-Tools
```

Output goes to `results/`: comparison tables (csv), route plots (png), per-vehicle route list
(`vrp_best_routes.csv`) and two interactive maps (open the html files in a browser, internet needed for map tiles).

## Methods

- **Nearest neighbour** - always go to the closest unvisited stop.
- **2-opt** - repeatedly reverse a section of the route if that shortens it, until nothing improves.
- **Genetic algorithm** - population of routes, tournament selection, order crossover, swap/reverse
  mutation, elitism. The first generation includes the nearest-neighbour tour plus random ones.
- **Capacity-aware greedy** - fill one vehicle at a time with the nearest stop that still fits.
- **Sweep** - order stops by angle around the depot, start a new vehicle when the current one is full.
- **Relocate** - move a single stop from one route to another when that lowers total distance and capacity allows.
- **Google OR-Tools** (optional) - routing solver with guided local search, used as a reference.

## Project layout

```
run.py                          runs everything
src/data.py                     loads locations.csv
src/distance.py                 distance matrix (haversine / OSRM)
src/tsp.py                      TSP methods
src/vrp.py                      CVRP methods
src/viz.py                      plots and html maps
scripts/fetch_road_distances.py optional real road distances
data/locations.csv              stops, coordinates, parcels
results/                        generated output
```

## Limitations

- Distances are estimated, not real road distances, unless you run the OSRM script.
- Parcel quantities are simulated.
- No time windows, traffic, or different vehicle types.
- The relocate step only moves one stop at a time; stronger moves (swap between routes, Or-opt)
  would probably find shorter routes.
- Only one problem size (45 stops) was tested.

## Ideas for extending it

- Add time windows and delivery deadlines.
- Compare against OR-Tools on bigger instances (100+ stops).
- Streamlit front end where a user picks stops on a map.
- Use real order data and real road distances.
