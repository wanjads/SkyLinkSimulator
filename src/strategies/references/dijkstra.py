import heapq
import math
from src.strategies.strategy import Strategy


class Dijkstra(Strategy):

    def __init__(self):
        self.strategy_name = "dijkstra"

    def set_targets(self, satellites, groundstations, current_time):

        distances = {node.id: float('inf') for node in satellites}
        previous = {node.id: None for node in satellites}

        priority_queue = []

        for satellite in satellites:

            for gs_id in satellite.GSL_connections:
                gs = groundstations[gs_id - len(satellites)]
                initial_distance = satellite.state.distance_to(gs.state)
                if initial_distance < distances[satellite.id]:
                    distances[satellite.id] = initial_distance
                    previous[satellite.id] = gs.id
            if distances[satellite.id] < math.inf:
                priority_queue += [(distances[satellite.id], satellite)]

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_distance > distances[current_node.id]:
                continue

            for sat_id in current_node.ISL_connections:
                sat = satellites[sat_id]
                distance = current_distance + current_node.state.distance_to(sat.state)

                if distance < distances[sat.id]:
                    distances[sat.id] = distance
                    previous[sat.id] = current_node.id
                    heapq.heappush(priority_queue, (distance, sat))

        for satellite in satellites:
            if previous[satellite.id] is not None:
                satellite.target_ids = [previous[satellite.id]]
