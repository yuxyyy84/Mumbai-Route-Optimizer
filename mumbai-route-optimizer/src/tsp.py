"""Single-vehicle routing (TSP): one vehicle visits every stop and returns to the depot.

A tour is a list of node ids that starts at the depot (0). The trip back to the
depot is implied, so the depot is not repeated at the end.
"""
import numpy as np


def tour_length(tour, D):
    t = np.asarray(tour)
    return float(D[t, np.roll(t, -1)].sum())


def random_tour(n, rng):
    return [0] + list(rng.permutation(np.arange(1, n)))


def nearest_neighbor(D, start=0):
    n = len(D)
    unvisited = set(range(n))
    unvisited.remove(start)
    tour = [start]
    while unvisited:
        last = tour[-1]
        nxt = min(unvisited, key=lambda j: D[last][j])
        tour.append(nxt)
        unvisited.remove(nxt)
    return tour


def two_opt(tour, D):
    """Keep reversing segments of the tour as long as that makes it shorter."""
    tour = list(tour)
    n = len(tour)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a, b = tour[i - 1], tour[i]
                c, d = tour[j], tour[(j + 1) % n]
                delta = D[a][c] + D[b][d] - D[a][b] - D[c][d]
                if delta < -1e-9:
                    tour[i:j + 1] = tour[i:j + 1][::-1]
                    improved = True
    return tour


# ---------------------------------------------------------------- genetic algorithm

def _order_crossover(p1, p2, rng):
    n = len(p1)
    a, b = sorted(rng.choice(n, size=2, replace=False))
    child = np.full(n, -1)
    child[a:b + 1] = p1[a:b + 1]
    taken = set(p1[a:b + 1].tolist())
    rest = [g for g in p2 if g not in taken]
    child[child == -1] = rest
    return child


def _mutate(perm, rng):
    perm = perm.copy()
    i, j = sorted(rng.choice(len(perm), size=2, replace=False))
    if rng.random() < 0.5:
        perm[i], perm[j] = perm[j], perm[i]          # swap two stops
    else:
        perm[i:j + 1] = perm[i:j + 1][::-1]          # reverse a stretch
    return perm


def genetic_algorithm(D, pop_size=200, generations=1000, mutation_rate=0.6,
                      elite=5, tournament=5, seed=0, seed_tours=None):
    """Plain GA on permutations of the stops (depot is fixed at the start).

    Returns (best tour, list with the best length of every generation).
    """
    rng = np.random.default_rng(seed)
    n = len(D)
    pop = [rng.permutation(np.arange(1, n)) for _ in range(pop_size)]

    # optionally put a few good tours in the first generation
    for k, t in enumerate(seed_tours or []):
        pop[k] = np.array([x for x in t if x != 0])

    def length(perm):
        return tour_length(np.concatenate(([0], perm)), D)

    def pick(pop, lens):
        idx = rng.choice(len(pop), size=tournament, replace=False)
        return pop[idx[np.argmin(lens[idx])]]

    history = []
    for _ in range(generations):
        lens = np.array([length(p) for p in pop])
        order = np.argsort(lens)
        pop = [pop[i] for i in order]
        lens = lens[order]
        history.append(float(lens[0]))

        new_pop = [p.copy() for p in pop[:elite]]
        while len(new_pop) < pop_size:
            child = _order_crossover(pick(pop, lens), pick(pop, lens), rng)
            if rng.random() < mutation_rate:
                child = _mutate(child, rng)
            new_pop.append(child)
        pop = new_pop

    lens = np.array([length(p) for p in pop])
    best = pop[int(np.argmin(lens))]
    history.append(float(lens.min()))
    return [0] + best.tolist(), history


# ---------------------------------------------------------------- Google OR-Tools

def ortools_tsp(D, time_limit_s=10):
    """Returns a tour, or None if ortools is not installed / no solution found."""
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return None

    n = len(D)
    dist = np.round(D * 1000).astype(int).tolist()   # metres, OR-Tools wants ints

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def cost(i, j):
        return dist[manager.IndexToNode(i)][manager.IndexToNode(j)]

    routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(cost))

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit_s

    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None

    tour = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        tour.append(manager.IndexToNode(idx))
        idx = solution.Value(routing.NextVar(idx))
    return tour
