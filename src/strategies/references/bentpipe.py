from src.strategies.strategy import Strategy
from numpy import random


class BentPipe(Strategy):

    def __init__(self):
        self.strategy_name = "bent-pipe"

    def set_targets(self, satellites, groundstations, current_time):

        for s in satellites:
            if len(s.GSL_connections) > 0:
                nbs = list(s.GSL_connections)
                random.shuffle(nbs)
                s.target_ids = nbs
