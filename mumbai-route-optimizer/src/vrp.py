"""Multi-vehicle routing with a capacity limit (CVRP).

A solution is a list of routes. Each route is a list of stop ids WITHOUT the
depot - every vehicle starts and ends at node 0.
"""
import numpy as np

from .tsp import two_opt


def route_cost(route, D):
    if not route:
        return 0.0
    path = [0] + list(route) + [0]
    return float(sum(D[a][b] for a, b in zip(path[:-1], path[1:])))


def total_cost(routes, D):
    return sum(route_cost(r, D) for r in routes)


def route_load(route, demands):
    return int(sum(demands[i] for i in route))


# ---------------------------------------------------------------- construction

def greedy_routes(D, demands, capacity):
    """Fill one vehicle at a time: go to the nearest stop that still fits."""
    unvisited = set(range(1, len(D)))
    routes = []
    while unvisited:
        route, load, last = [], 0, 0
        while True:
            fits = [j for j in unvisited if load + demands[j] <= capacity]
            if not fits:
                break
            nxt = min(fits, key=lambda j: D[last][j])
            route.append(nxt)
            load += demands[nxt]
            unvisited.remove(nxt)
            last = nxt
        if not route:
            raise ValueError("a single stop is bigger than vehicle capacity")
        routes.append(route)
    return routes


def sweep_routes(df, demands, capacity):
    """Sort stops by angle around the depot and cut a new route whenever the vehicle is full."""
    d_lat = df["lat"] - df.loc[0, "lat"]
    d_lng = (df["lng"] - df.loc[0, "lng"]) * np.cos(np.radians(df.loc[0, "lat"]))
    angle = np.arctan2(d_lat, d_lng)
    order = sorted(range(1, len(df)), key=lambda i: angle[i])

    routes, current, load = [], [], 0
    for i in order:
        if load + demands[i] > capacity and current:
            routes.append(current)
            current, load = [], 0
        current.append(i)
        load += demands[i]
    if current:
        routes.append(current)
    return routes


# ---------------------------------------------------------------- improvement

def _two_opt_each_route(routes, D):
    out = []
    for r in routes:
        if len(r) > 2:
            r = two_opt([0] + r, D)[1:]
        out.append(r)
    return out


def _relocate_once(routes, D, demands, capacity):
    """Look for one stop that is cheaper in a different route. Apply the first one found."""
    loads = [route_load(r, demands) for r in routes]
    for a, ra in enumerate(routes):
        for i, node in enumerate(ra):
            prev_a = ra[i - 1] if i > 0 else 0
            next_a = ra[i + 1] if i + 1 < len(ra) else 0
            saving = D[prev_a][node] + D[node][next_a] - D[prev_a][next_a]

            for b, rb in enumerate(routes):
                if b == a or loads[b] + demands[node] > capacity:
                    continue
                for j in range(len(rb) + 1):
                    prev_b = rb[j - 1] if j > 0 else 0
                    next_b = rb[j] if j < len(rb) else 0
                    extra = D[prev_b][node] + D[node][next_b] - D[prev_b][next_b]
                    if extra < saving - 1e-9:
                        ra.pop(i)
                        rb.insert(j, node)
                        return True
    return False


def improve(routes, D, demands, capacity, max_rounds=200):
    routes = [list(r) for r in routes]
    for _ in range(max_rounds):
        routes = _two_opt_each_route(routes, D)
        moved = _relocate_once(routes, D, demands, capacity)
        routes = [r for r in routes if r]
        if not moved:
            break
    return _two_opt_each_route(routes, D)


def greedy_plus_local_search(D, demands, capacity):
    return improve(greedy_routes(D, demands, capacity), D, demands, capacity)


# ---------------------------------------------------------------- Google OR-Tools

def ortools_vrp(D, demands, capacity, n_vehicles, time_limit_s=15):
    """Returns routes (without depot), or None if ortools is missing / no solution."""
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return None

    n = len(D)
    dist = np.round(np.asarray(D) * 1000).astype(int).tolist()
    demands = [int(x) for x in demands]

    manager = pywrapcp.RoutingIndexManager(n, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def cost(i, j):
        return dist[manager.IndexToNode(i)][manager.IndexToNode(j)]

    def load(i):
        return demands[manager.IndexToNode(i)]

    routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(cost))
    load_cb = routing.RegisterUnaryTransitCallback(load)
    routing.AddDimensionWithVehicleCapacity(load_cb, 0, [int(capacity)] * n_vehicles, True, "Load")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit_s

    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None

    routes = []
    for v in range(n_vehicles):
        idx = routing.Start(v)
        route = []
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != 0:
                route.append(node)
            idx = solution.Value(routing.NextVar(idx))
        if route:
            routes.append(route)
    return routes
