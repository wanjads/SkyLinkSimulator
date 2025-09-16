import json
import math
from src.state import State
import numpy as np


class Groundstation:

    def __init__(self, gs_id):

        self.id = gs_id

        self.outgoing_throughput = 5e10  # estimated 50 Gbps fibre connections

        self.buffer_size = 8e9  # estimated 1GB buffer capacity
        self.buffer_level = 0

        self.incoming_streams = {}  # format: {incoming_node: [path,traffic], ...}
        self.outgoing_streams = {}

        self.delay_lower_limit = 1  # estimated 1 ms
        self.delay_upper_limit = 5  # estimated 5 ms

        self.delay = np.random.uniform(self.delay_lower_limit, self.delay_upper_limit)
        self.drop_rate = 0

        self.state = None

        self.failed = False

    def state_update(self, x, y, z):
        long = math.degrees(math.atan2(y, x))

        hyp = math.sqrt(x ** 2 + y ** 2)
        lat = math.degrees(math.atan2(z, hyp))

        self.state = State(long, lat, x, y, z)

    def update_buffer(self):
        outgoing_traffic = sum(map(lambda s: s[1], [s for ss in self.outgoing_streams.values() for s in ss]))

        if outgoing_traffic >= self.outgoing_throughput:
            self.buffer_level = self.buffer_size
        else:
            self.buffer_level = 0

    def update_delay(self):

        center = (self.delay_lower_limit + self.delay_upper_limit) / 2
        sigma = (self.delay_upper_limit - self.delay_lower_limit) / 6

        # gaussian disturbance
        self.delay = self.delay + np.random.normal(0, sigma)

        # pull towards center
        self.delay += (center - self.delay) * 0.1

        # keep boundaries
        self.delay = max(min(self.delay, self.delay_upper_limit), self.delay_lower_limit)

        queuing_delay = self.buffer_level / self.outgoing_throughput

        self.delay += queuing_delay

    def logging(self, file_path, time):
        data = {
            "time": time,
            "self_id": self.id,
            "position": (round(self.state.x, 4), round(self.state.y, 4), round(self.state.z, 4)),
            "outgoing_throughput": self.outgoing_throughput,
            "incoming_streams": json.dumps({key: round(sum(map(lambda x: x[1], value)))
                                            for key, value in self.incoming_streams.items()}),
            "outgoing_streams": json.dumps({key: round(sum(map(lambda x: x[1], value)))
                                            for key, value in self.outgoing_streams.items()}),
            "delay": self.delay,
            "drop_rate": self.drop_rate
        }

        csv_row = ';'.join(str(data[key]) for key in data.keys())

        with open(file_path, "a") as file:
            file.write(csv_row + "\n")
