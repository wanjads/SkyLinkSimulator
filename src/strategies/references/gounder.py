import heapq
from src.strategies.strategy import Strategy


class Gounder(Strategy):

    def __init__(self):
        self.strategy_name = "gounder"
        self.K = 4

    def set_targets(self, satellites, groundstations, current_time):

        neighbours_distances = {node.id: [] for node in satellites}

        priority_queue = []

        for satellite in satellites:

            for gs_id in satellite.GSL_connections:
                gs = groundstations[gs_id - len(satellites)]
                initial_distance = satellite.state.distance_to(gs.state)
                if (len(neighbours_distances[satellite.id]) < self.K
                        or initial_distance < neighbours_distances[satellite.id][-1][1]):
                    neighbours_distances[satellite.id] += [(gs, initial_distance)]
                    neighbours_distances[satellite.id] = sorted(neighbours_distances[satellite.id], key=lambda x: x[1])
                    if len(neighbours_distances[satellite.id]) > self.K:
                        neighbours_distances[satellite.id] = neighbours_distances[satellite.id][:-1]
            if len(neighbours_distances[satellite.id]) > 0:
                shortest_distance = neighbours_distances[satellite.id][0][1]
                priority_queue += [(shortest_distance, satellite)]

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_distance > neighbours_distances[current_node.id][-1][1]:
                continue

            for sat_id in current_node.ISL_connections:
                sat = satellites[sat_id]
                distance = current_distance + current_node.state.distance_to(sat.state)
                if (len(neighbours_distances[sat_id]) < self.K or
                        distance < neighbours_distances[sat_id][-1][1]):
                    if len(neighbours_distances[sat_id]) == 0 or distance < neighbours_distances[sat_id][0][1]:
                        heapq.heappush(priority_queue, (distance, sat))
                    if current_node.id not in list(map(lambda x: x[0].id, neighbours_distances[sat.id])):
                        neighbours_distances[sat_id] += [(current_node, distance)]
                    else:
                        for n, d in neighbours_distances[sat_id]:
                            if n.id == current_node.id:
                                if distance < d:
                                    neighbours_distances[sat_id].remove((n, d))
                                    neighbours_distances[sat_id] += [(n, distance)]
                                break
                    neighbours_distances[sat_id] = \
                        sorted(neighbours_distances[sat_id], key=lambda x: x[1])
                    if len(neighbours_distances[sat_id]) > self.K:
                        neighbours_distances[sat_id] = neighbours_distances[sat_id][:-1]

        for satellite in satellites:
            satellite.target_ids = list(map(lambda x: x[0].id, neighbours_distances[satellite.id]))
