import heapq
import math
from datetime import timedelta

import numpy as np
from src.strategies.strategy import Strategy


class TileCodedUCB(Strategy):

    def __init__(self, contexts, distance_precision, no_of_grids):
        self.strategy_name = "tile_coded_ucb" + f"_{int(distance_precision):07}_" + str(no_of_grids)

        # UCB variables
        self.uncertainty_factor = 1
        self.tiles = {}

        # context parameters
        self.contexts = contexts  # ['distance']
        self.distance_precision = distance_precision * no_of_grids  # 900_000  # in m, original 180_000 * 5 = 900_000
        self.data_precision_base = 30  # 30
        self.time_precision = 3600  # in seconds
        self.total_distance_precision = 1_000_000  # in m
        self.elev_precision = 10_000  # in m

        # tiling parameters
        self.no_of_grids = no_of_grids  # 5

        self.counter_cap = 1e10

    def set_targets(self, satellites, groundstations, current_time):

        dijkstra_targets = None
        distances = None
        if "dijkstra" in self.contexts or "total_distance" in self.contexts or "order" in self.contexts:
            distances = {node.id: float('inf') for node in satellites}
            dijkstra_targets = {node.id: None for node in satellites}

            priority_queue = []

            for satellite in satellites:

                for gs_id in satellite.GSL_connections:
                    gs = groundstations[gs_id - len(satellites)]
                    initial_distance = satellite.state.distance_to(gs.state)
                    if initial_distance < distances[satellite.id]:
                        distances[satellite.id] = initial_distance
                        dijkstra_targets[satellite.id] = gs.id
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
                        dijkstra_targets[sat.id] = current_node.id
                        heapq.heappush(priority_queue, (distance, sat))

            for gs in groundstations:
                distances[gs.id] = 0
            for sat in satellites:
                if math.isinf(distances[sat.id]):
                    distances[sat.id] = 1e8

        if len(self.tiles) == 0:
            for sat in satellites:
                self.tiles[sat] = {}

        for sat in satellites:

            targets_sorted_by_distance = None
            if "order" in self.contexts:
                target_ids = [int(i) for i in np.concatenate((sat.ISL_connections, sat.GSL_connections))]
                targets_sorted_by_distance = (
                    sorted(target_ids,
                           key=lambda t_id:
                           distances[int(t_id)] + sat.state.distance_to(satellites[t_id].state)
                           if int(t_id) in sat.ISL_connections else
                           distances[int(t_id)] + sat.state.distance_to(groundstations[t_id - len(satellites)].state)))

            total_selections = [0 for _ in range(self.no_of_grids)]
            cost_count_per_target = [{} for _ in range(self.no_of_grids)]
            for target_id in np.concatenate((sat.ISL_connections, sat.GSL_connections)):
                target_id = int(target_id)

                if target_id not in self.tiles[sat]:
                    self.tiles[sat][target_id] = {}

                if target_id in sat.ISL_connections:
                    target = satellites[target_id]
                else:
                    target = groundstations[target_id - len(satellites)]

                if "elevation" in self.contexts:
                    elev = (sat.state.x^2 + sat.state.y^2 + sat.state.z^2) - 6371000
                else:
                    elev = 0

                if "distance" in self.contexts:
                    distance = sat.state.distance_to(target.state)
                else:
                    distance = 0

                if "data" in self.contexts:
                    data = sat.generation_rate
                else:
                    data = 0

                if "local_time" in self.contexts:
                    offset = int((sat.state.long + 180) / 15) - 12
                    local_time = current_time.to_datetime() + timedelta(hours=offset)
                    t = int(local_time.hour) * 3600 + int(local_time.minute) * 60 + int(local_time.second)
                else:
                    t = 0

                if "utc_time" in self.contexts:
                    utc_time = current_time.to_datetime()
                    u = int(utc_time.hour) * 3600 + int(utc_time.minute) * 60 + int(utc_time.second)
                else:
                    u = 0

                if "dijkstra" in self.contexts:
                    dijkstra = target_id == dijkstra_targets[sat.id]
                else:
                    dijkstra = 0

                if "total_distance" in self.contexts:
                    total_distance = distances[target.id] + sat.state.distance_to(target.state)
                else:
                    total_distance = 0

                if "order" in self.contexts:
                    order = int(targets_sorted_by_distance.index(target_id) == 0)
                else:
                    order = 0

                for grid_no in range(self.no_of_grids):
                    context = (int(distance / self.distance_precision + grid_no / self.no_of_grids)
                               - grid_no / self.no_of_grids,
                               int(math.log(data + 1, self.data_precision_base) + grid_no / self.no_of_grids)
                               - grid_no / self.no_of_grids,
                               int(t / self.time_precision + grid_no / self.no_of_grids)
                               - grid_no / self.no_of_grids,
                               int(u / self.time_precision + grid_no / self.no_of_grids)
                               - grid_no / self.no_of_grids,
                               dijkstra,
                               order,
                               int(total_distance / self.total_distance_precision + grid_no / self.no_of_grids)
                               - grid_no / self.no_of_grids,
                               int(elev / self.elev_precision + grid_no / self.no_of_grids)
                               - grid_no / self.no_of_grids)

                    if context not in self.tiles[sat][target_id]:
                        self.tiles[sat][target_id][context] = [0, 0]

                    cost_count_per_target[grid_no][target_id] = self.tiles[sat][target_id][context]
                    total_selections[grid_no] += cost_count_per_target[grid_no][target_id][1]

            targets = []
            for target_id in np.concatenate((sat.ISL_connections, sat.GSL_connections)):
                target_id = int(target_id)

                ucb_value = 0
                for grid_no in range(self.no_of_grids):
                    avg_cost, selection_count = cost_count_per_target[grid_no][target_id]
                    if selection_count > 0:
                        ucb_value += (avg_cost - self.uncertainty_factor *
                                      math.sqrt(2 * math.log(total_selections[grid_no]) / selection_count))
                    else:
                        ucb_value = -math.inf
                        break

                targets += [[target_id, ucb_value / self.no_of_grids]]

            sorted_targets = sorted(targets, key=lambda x: x[1])

            if len(sorted_targets) > 0:
                sat.target_ids = list(map(lambda x: x[0], sorted_targets))
            else:
                sat.target_ids = []

    def learn(self, satellites, groundstations, current_time):

        dijkstra_targets = None
        distances = None
        if "dijkstra" in self.contexts or "total_distance" in self.contexts or "order" in self.contexts:
            distances = {node.id: float('inf') for node in satellites}
            dijkstra_targets = {node.id: None for node in satellites}

            priority_queue = []

            for satellite in satellites:

                for gs_id in satellite.GSL_connections:
                    gs = groundstations[gs_id - len(satellites)]
                    initial_distance = satellite.state.distance_to(gs.state)
                    if initial_distance < distances[satellite.id]:
                        distances[satellite.id] = initial_distance
                        dijkstra_targets[satellite.id] = gs.id
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
                        dijkstra_targets[sat.id] = current_node.id
                        heapq.heappush(priority_queue, (distance, sat))

            for gs in groundstations:
                distances[gs.id] = 0
            for sat in satellites:
                if math.isinf(distances[sat.id]):
                    distances[sat.id] = 1e8

        for sat in satellites:

            targets_sorted_by_distance = None
            if "order" in self.contexts:
                target_ids = [int(i) for i in np.concatenate((sat.ISL_connections, sat.GSL_connections))]
                targets_sorted_by_distance = (
                    sorted(target_ids,
                           key=lambda t_id:
                           distances[int(t_id)] + sat.state.distance_to(satellites[t_id].state)
                           if int(t_id) in sat.ISL_connections else
                           distances[int(t_id)] + sat.state.distance_to(groundstations[t_id - len(satellites)].state)))

            if sat.cost > 0:
                if len(sat.target_ids) > 0:
                    target_id = sat.target_ids[0]
                    if target_id is not None:

                        if target_id in sat.ISL_connections:
                            target = satellites[target_id]
                        else:
                            target = groundstations[target_id - len(satellites)]

                        if "elevation" in self.contexts:
                            elev = (sat.state.x^2 + sat.state.y^2 + sat.state.z^2) - 6371000
                        else:
                            elev = 0

                        if "distance" in self.contexts:
                            distance = sat.state.distance_to(target.state)
                        else:
                            distance = 0

                        if "data" in self.contexts:
                            data = sat.generation_rate
                        else:
                            data = 0

                        if "local_time" in self.contexts:
                            offset = int((sat.state.long + 180) / 15) - 12
                            local_time = current_time.to_datetime() + timedelta(hours=offset)
                            t = int(local_time.hour) * 3600 + int(local_time.minute) * 60 + int(local_time.second)
                        else:
                            t = 0

                        if "utc_time" in self.contexts:
                            utc_time = current_time.to_datetime()
                            u = int(utc_time.hour) * 3600 + int(utc_time.minute) * 60 + int(utc_time.second)
                        else:
                            u = 0

                        if "dijkstra" in self.contexts:
                            dijkstra = target_id == dijkstra_targets[sat.id]
                        else:
                            dijkstra = 0

                        if "total_distance" in self.contexts:
                            total_distance = distances[target.id] + sat.state.distance_to(target.state)
                        else:
                            total_distance = 0

                        if "order" in self.contexts:
                            order = int(targets_sorted_by_distance.index(target_id) == 0)
                        else:
                            order = 0

                        for grid_no in range(self.no_of_grids):
                            context = (int(distance / self.distance_precision + grid_no / self.no_of_grids)
                                       - grid_no / self.no_of_grids,
                                       int(math.log(data + 1, self.data_precision_base) + grid_no / self.no_of_grids)
                                       - grid_no / self.no_of_grids,
                                       int(t / self.time_precision + grid_no / self.no_of_grids)
                                       - grid_no / self.no_of_grids,
                                       int(u / self.time_precision + grid_no / self.no_of_grids)
                                       - grid_no / self.no_of_grids,
                                       dijkstra,
                                       order,
                                       int(total_distance / self.total_distance_precision + grid_no / self.no_of_grids)
                                       - grid_no / self.no_of_grids,
                                       int(elev / self.elev_precision + grid_no / self.no_of_grids)
                                      - grid_no / self.no_of_grids
                            )

                            old_estimate, n = self.tiles[sat][target_id][context]
                            self.tiles[sat][target_id][context][0] = (
                                    (n * old_estimate + sat.cost) / (n + 1))
                            if n <= self.counter_cap:
                                self.tiles[sat][target_id][context][1] = n + 1
