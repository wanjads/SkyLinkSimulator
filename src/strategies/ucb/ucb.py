import math
import numpy as np
from src.strategies.strategy import Strategy


class UCB(Strategy):

    def __init__(self):
        self.strategy_name = "ucb"

        # UCB variables
        self.uncertainty_factor = 1
        self.cost_estimates = {}  # format: {satellite: {nodeID: [cost estimate, number of usages]}}

        self.counter_cap = 1e10

    def set_targets(self, satellites, groundstations, current_time):

        if len(self.cost_estimates) == 0:
            for sat in satellites:
                self.cost_estimates[sat] = {}

        for sat in satellites:

            total_selections = sum([value[1] for value in self.cost_estimates[sat].values()])

            targets = []
            for target_id in np.concatenate((sat.ISL_connections, sat.GSL_connections)):
                target_id = int(target_id)

                if target_id not in self.cost_estimates[sat]:
                    self.cost_estimates[sat][target_id] = [0, 0]

                avg_cost, selection_count = self.cost_estimates[sat][target_id]
                if selection_count > 0:
                    ucb_value = (avg_cost - self.uncertainty_factor *
                                 math.sqrt(2 * math.log(total_selections) / selection_count))
                else:
                    ucb_value = -math.inf
                targets += [[target_id, ucb_value]]

            sorted_targets = sorted(targets, key=lambda x: x[1])

            if len(sorted_targets) > 0:
                sat.target_ids = list(map(lambda x: x[0], sorted_targets))
            else:
                sat.target_ids = []

    def learn(self, satellites, groundstations, current_time):

        for sat in satellites:
            if sat.cost > 0:
                if len(sat.target_ids) > 0:
                    target_id = sat.target_ids[0]
                    if target_id is not None:
                        old_estimate, n = self.cost_estimates[sat][target_id]
                        self.cost_estimates[sat][target_id][0] = (n * old_estimate + sat.cost) / (n + 1)
                        if self.cost_estimates[sat][target_id][1] <= self.counter_cap:
                            self.cost_estimates[sat][target_id][1] += 1

    def reset(self, satellites):
        self.cost_estimates = {}
