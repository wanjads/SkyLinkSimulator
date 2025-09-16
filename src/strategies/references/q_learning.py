from collections import defaultdict
import numpy as np
from src.strategies.strategy import Strategy

def _q_level2():
    return defaultdict(float)

def _q_level1():
    return defaultdict(_q_level2)

class QLearning(Strategy):

    def __init__(self,
                 alpha=0.15,
                 gamma=0.90,
                 epsilon=0.15,
                 epsilon_min=0.02,
                 epsilon_decay=0.9995):
        self.strategy_name = "q_learning"
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        self.Q = defaultdict(_q_level1)
        self.last_state = {}
        self.last_action = {}
        self.steps = defaultdict(int)

    def reset(self, satellites):
        self.Q.clear()
        self.last_state.clear()
        self.last_action.clear()
        self.steps.clear()

    def set_targets(self, satellites, groundstations, current_time):

        for sat in satellites:
            actions = self._available_actions(sat)
            if not actions:
                sat.target_ids = []
                continue

            s_key = self._state_key(sat, satellites, groundstations, current_time)
            self.steps[sat.id] += 1

            if np.random.random() < self.epsilon:
                a = np.random.choice(actions)
            else:
                a = self._argmax_q(sat.id, s_key, actions)

            ranked = self._rank_actions_by_q(sat.id, s_key, actions, chosen_first=a)
            sat.target_ids = ranked

            self.last_state[sat.id] = s_key
            self.last_action[sat.id] = a

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def learn(self, satellites, groundstations, current_time):
        for sat in satellites:
            if sat.id in self.last_state and sat.id in self.last_action and getattr(sat, "cost", 0) != 0:
                s_prev = self.last_state[sat.id]
                a_prev = self.last_action[sat.id]

                r = - float(sat.cost)

                s_next = self._state_key(sat, satellites, groundstations, current_time)
                next_actions = self._available_actions(sat)
                if next_actions:
                    q_next_max = max(self.Q[sat.id][s_next][a_] for a_ in next_actions)
                else:
                    q_next_max = 0.0

                q_old = self.Q[sat.id][s_prev][a_prev]
                q_new = (1 - self.alpha) * q_old + self.alpha * (r + self.gamma * q_next_max)
                self.Q[sat.id][s_prev][a_prev] = q_new

    @staticmethod
    def _available_actions(sat):
        actions = list(map(int, np.concatenate((sat.ISL_connections, sat.GSL_connections))))
        return list(dict.fromkeys(actions))

    def _argmax_q(self, sat_id, s_key, actions):
        best_a, best_q = None, -float("inf")
        for a in sorted(actions):
            q = self.Q[sat_id][s_key][a]
            if q > best_q:
                best_q, best_a = q, a
        return best_a

    def _rank_actions_by_q(self, sat_id, s_key, actions, chosen_first=None):
        scored = [(a, self.Q[sat_id][s_key][a]) for a in actions]
        scored.sort(key=lambda t: (-t[1], t[0]))
        ranked = [a for a, _ in scored]
        if chosen_first is not None and chosen_first in ranked:
            ranked.remove(chosen_first)
            ranked.insert(0, chosen_first)
        return ranked

    def _state_key(self, sat, satellites, groundstations, current_time):
        deg_isl_bin = self._bin_deg_isl(len(sat.ISL_connections))
        deg_gsl_bin = self._bin_deg_gsl(len(sat.GSL_connections))
        min_gsl_dist_bin = self._bin_min_gsl_distance(sat, groundstations, len(satellites))
        best_isl_cap_bin = self._bin_best_isl_capacity(sat, satellites)
        tod_bin = self._bin_time_of_day(current_time.to_datetime().hour)
        return (deg_isl_bin, deg_gsl_bin, min_gsl_dist_bin, best_isl_cap_bin, tod_bin)

    @staticmethod
    def _bin_deg_isl(deg):
        if deg <= 0: return 0
        if deg <= 2: return 1
        if deg <= 4: return 2
        return 3

    @staticmethod
    def _bin_deg_gsl(deg):
        if deg <= 0: return 0
        if deg == 1: return 1
        return 2

    @staticmethod
    def _bin_time_of_day(hour):
        return int(hour // 4)  # {0..5}

    def _bin_min_gsl_distance(self, sat, groundstations, n_sats):
        if not sat.GSL_connections:
            return 9
        dists = []
        for gs_id in sat.GSL_connections:
            gs = groundstations[int(gs_id) - n_sats]
            dists.append(sat.state.distance_to(gs.state))
        d_km = min(dists) / 1000.0
        return int(min(8, d_km // 1000))

    def _bin_best_isl_capacity(self, sat, satellites):
        if len(sat.ISL_connections) == 0:
            return 0
        caps = []
        for nb_id in sat.ISL_connections:
            nb = satellites[int(nb_id)]
            dist = sat.state.distance_to(nb.state)
            try:
                cap = sat.isl_capacity(dist)
            except Exception:
                cap = 0.0
            caps.append(max(0.0, float(cap)))
        cap_gbps = max(caps) / 1e9
        if cap_gbps <= 0: return 0
        if cap_gbps <= 0.5: return 1
        if cap_gbps <= 1.0: return 2
        if cap_gbps <= 2.0: return 3
        return 4
