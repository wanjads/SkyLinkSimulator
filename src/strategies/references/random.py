from numpy import random
from src.strategies.strategy import Strategy


class Random(Strategy):

    def __init__(self):
        self.strategy_name = "random"

    def set_targets(self, satellites, groundstations, current_time):

        for s in satellites:
            if len(s.ISL_connections) + len(s.GSL_connections) > 0:
                nbs = list(s.ISL_connections)
                nbs += list(s.GSL_connections)
                random.shuffle(nbs)
                s.target_ids = nbs
