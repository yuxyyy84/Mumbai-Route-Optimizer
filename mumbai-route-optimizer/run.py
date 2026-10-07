"""Run all the solvers on the Mumbai delivery data and save tables, plots and maps.

    python run.py
    python run.py --vehicles 5 --capacity 60
    python run.py --no-ortools
"""
import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src import tsp, vrp, viz
from src.data import load_locations
from src.distance import build_matrix

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, time.perf_counter() - t0


def run_tsp(df, D, args):
    n = len(D)
    print("\n=== Part 1: one vehicle, all %d stops (TSP) ===" % (n - 1))

    rng = np.random.default_rng(args.seed)
    random_lengths = [tsp.tour_length(tsp.random_tour(n, rng), D) for _ in range(500)]
    results = [("Random order (avg of 500)", float(np.mean(random_lengths)), 0.0, None)]

    nn, t = timed(tsp.nearest_neighbor, D)
    results.append(("Nearest neighbour", tsp.tour_length(nn, D), t, nn))

    nn2, t2 = timed(tsp.two_opt, nn, D)
    results.append(("Nearest neighbour + 2-opt", tsp.tour_length(nn2, D), t + t2, nn2))

    (ga_tour, history), t = timed(tsp.genetic_algorithm, D, generations=args.generations,
                                  seed=args.seed, seed_tours=[nn])
    results.append(("Genetic algorithm", tsp.tour_length(ga_tour, D), t, ga_tour))

    if not args.no_ortools:
        ot, t = timed(tsp.ortools_tsp, D, args.ortools_seconds)
        if ot is None:
            print("(ortools not installed - skipping it. pip install ortools)")
        else:
            results.append(("Google OR-Tools", tsp.tour_length(ot, D), t, ot))

    base = results[0][1]
    table = pd.DataFrame([
        {"method": name, "distance_km": round(length, 2),
         "vs_random_%": round((1 - length / base) * 100, 1), "runtime_s": round(sec, 2)}
        for name, length, sec, _ in results
    ])
    print(table.to_string(index=False))
    table.to_csv(RESULTS / "tsp_comparison.csv", index=False)

    best_name, best_len, _, best_tour = min((r for r in results if r[3] is not None), key=lambda r: r[1])
    print(f"best tour: {best_name}, {best_len:.2f} km")

    viz.plot_tour(df, nn, "Nearest neighbour", RESULTS / "tsp_nearest_neighbour.png")
    viz.plot_tour(df, best_tour, f"Best tour: {best_name} ({best_len:.1f} km)", RESULTS / "tsp_best_tour.png")
    viz.plot_convergence(history, tsp.tour_length(nn, D), tsp.tour_length(nn2, D), RESULTS / "ga_convergence.png")
    viz.plot_bar(table["method"], table["distance_km"], "TSP: total distance by method", RESULTS / "tsp_comparison.png")
    viz.write_map(df, [best_tour], f"TSP best tour - {best_name}", RESULTS / "tsp_map.html")


def run_vrp(df, D, args):
    demands = df["parcels"].tolist()
    total = sum(demands)
    capacity = args.capacity
    print("\n=== Part 2: %d vehicles, capacity %d parcels each (CVRP) ===" % (args.vehicles, capacity))
    print("total parcels: %d, fleet capacity: %d" % (total, capacity * args.vehicles))
    if total > capacity * args.vehicles:
        print("warning: parcels do not fit in the fleet, greedy will open extra vehicles")

    results = []
    greedy, t = timed(vrp.greedy_routes, D, demands, capacity)
    results.append(("Greedy capacity-aware NN", greedy, t))

    better, t2 = timed(vrp.improve, greedy, D, demands, capacity)
    results.append(("Greedy + 2-opt + relocate", better, t + t2))

    sw, t = timed(vrp.sweep_routes, df, demands, capacity)
    sw_better, t2 = timed(vrp.improve, sw, D, demands, capacity)
    results.append(("Sweep + 2-opt + relocate", sw_better, t + t2))

    if not args.no_ortools:
        orr, t = timed(vrp.ortools_vrp, D, demands, capacity, args.vehicles, args.ortools_seconds)
        if orr is None:
            print("(ortools not installed - skipping it)")
        else:
            results.append(("Google OR-Tools", orr, t))

    base = vrp.total_cost(greedy, D)
    table = pd.DataFrame([
        {"method": name, "distance_km": round(vrp.total_cost(r, D), 2), "vehicles_used": len(r),
         "vs_greedy_%": round((1 - vrp.total_cost(r, D) / base) * 100, 1), "runtime_s": round(sec, 2)}
        for name, r, sec in results
    ])
    print(table.to_string(index=False))
    table.to_csv(RESULTS / "vrp_comparison.csv", index=False)

    best_name, best_routes, _ = min(results, key=lambda r: vrp.total_cost(r[1], D))
    print(f"\nbest: {best_name}")
    rows = []
    for k, r in enumerate(best_routes, 1):
        print("  vehicle %d: %2d stops, load %d/%d, %.1f km" %
              (k, len(r), vrp.route_load(r, demands), capacity, vrp.route_cost(r, D)))
        rows.append({"vehicle": k, "stops": len(r), "load": vrp.route_load(r, demands),
                     "distance_km": round(vrp.route_cost(r, D), 2),
                     "route": " > ".join(["Depot"] + [df.loc[i, "name"] for i in r] + ["Depot"])})
    pd.DataFrame(rows).to_csv(RESULTS / "vrp_best_routes.csv", index=False)

    viz.plot_routes(df, greedy, "Greedy routes", RESULTS / "vrp_greedy.png")
    viz.plot_routes(df, best_routes, f"Best: {best_name}", RESULTS / "vrp_best.png")
    viz.plot_bar(table["method"], table["distance_km"], "CVRP: total distance by method", RESULTS / "vrp_comparison.png")
    viz.write_map(df, best_routes, f"CVRP best routes - {best_name}", RESULTS / "vrp_map.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--generations", type=int, default=1000)
    ap.add_argument("--vehicles", type=int, default=4)
    ap.add_argument("--capacity", type=int, default=75)
    ap.add_argument("--ortools-seconds", type=int, default=10)
    ap.add_argument("--no-ortools", action="store_true")
    ap.add_argument("--road-matrix", default=str(ROOT / "data" / "road_matrix.json"))
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    df = load_locations()
    D, source = build_matrix(df, args.road_matrix)
    print("%d stops + depot, distances: %s" % (len(df) - 1, source))

    run_tsp(df, D, args)
    run_vrp(df, D, args)
    print("\nDone. Files are in results/")


if __name__ == "__main__":
    main()
