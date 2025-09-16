import json
import math
import numpy as np
from src.state import State


class Satellite:
    atmospheric_attenuation: np.array

    def __init__(self, sat_id):

        self.id = sat_id

        self.visible_groundstations = []

        self.ISL_connections = []
        self.GSL_connections = []

        self.state = None

        self.generation_rate = 0

        self.buffer_size = 4e8  # estimated 50MB buffer capacity

        self.buffer_level = 0

        self.target_ids = []
        self.outgoing_throughputs = {}

        self.delay = 0
        self.delays_per_outgoing_link = {}
        self.drops_per_link = []
        self.drop_rate = 0
        self.local_drop_rate = 0
        self.incoming_data = 0
        self.cost = 0

        self.incoming_streams = {}  # format: {incoming_node: [path,traffic], ...}
        self.outgoing_streams = {}

        # ISL parameters
        self.k = 1.38e-23  # Boltzmann constant in J/K
        self.isl_bandwidth = 5e9  # 5 GHz
        self.power = 0.1  # 0.1 W
        self.aperture_diameter = 0.1  # 10 cm
        self.noise_temperature = 290  # 290 K (standard temperature)
        self.beam_divergence = 1.744e-5  # Divergence in radians
        self.pointing_loss = 0.9  # Pointing accuracy factor

        # GSL parameter
        self.speed_of_light = 299792458  # in m/s
        self.k = 1.38e-23  # Boltzmann constant in J/K
        self.T_mr = 275  # K
        self.EIRP = 34.6  # dbW
        self.G_rx = 10.8  # db
        self.carrier_f = 19  # GHz
        self.gsl_bandwidth = 250e6

        self.min_elevation = 20  # in degrees
        self.max_elevation = 90  # in degrees
        self.step_elevation = 0.1

        self.failed_isl = False
        self.failed_gsl = False

    def state_update(self, x, y, z):

        # Calculate longitude (in degrees)
        long = math.degrees(math.atan2(y, x))

        # Calculate latitude (in degrees)
        hyp = math.sqrt(x ** 2 + y ** 2)
        lat = math.degrees(math.atan2(z, hyp))

        self.state = State(long, lat, x, y, z)

    def update_buffer(self, satellites, groundstations):
        outgoing_traffic = sum(map(lambda s: s[1], [s for ss in self.outgoing_streams.values() for s in ss]))
        outgoing_capacity = 0

        for target in self.target_ids:
            if target >= len(satellites):
                outgoing_capacity += min(self.outgoing_throughputs[target],
                                         self.gsl_capacity(groundstations[target - len(satellites)], satellites))
            else:
                outgoing_capacity += min(self.outgoing_throughputs[target],
                                         self.isl_capacity(self.state.distance_to(satellites[target].state)))

        if outgoing_traffic >= outgoing_capacity:
            self.buffer_level = self.buffer_size
        else:
            self.buffer_level = 0

    def update_generation_rate(self, data_generation_matrix, growth_factor=1):
        self.generation_rate = growth_factor * data_generation_matrix[self.id]

    def isl_capacity(self, distance):

        effective_area = np.pi * (self.aperture_diameter / 2) ** 2
        received_power_density = self.power / (np.pi * (distance * self.beam_divergence) ** 2)
        received_power = received_power_density * effective_area * self.pointing_loss
        noise_power = self.k * self.noise_temperature * self.isl_bandwidth
        capacity = 0.08 * self.isl_bandwidth * np.log2(1 + received_power / noise_power)  # 0.08 = upload factor

        return 1 if self.failed_isl else capacity

    def update_outgoing_throughput(self, groundstations, satellites):

        self.outgoing_throughputs = {}

        for target_id in self.target_ids:
            if target_id in self.ISL_connections:
                dist = self.state.distance_to(satellites[target_id].state)
                self.outgoing_throughputs[target_id] = self.isl_capacity(dist)
            elif target_id in self.GSL_connections:
                gs = groundstations[target_id - len(satellites)]
                self.outgoing_throughputs[target_id] = self.gsl_capacity(gs, satellites)

            if self.outgoing_throughputs[target_id] < 0:
                self.outgoing_throughputs[target_id] = 0

    def gsl_capacity(self, gs, satellites):
        # atmospheric attenuation
        gs_position = gs.state.as_vector()
        sat_gs_vector = self.state.as_vector() - gs_position
        d = np.linalg.norm(sat_gs_vector)
        angle = np.arccos(np.sum(sat_gs_vector * gs_position) /
                          (d * np.linalg.norm(gs_position)))
        elevation = 90 - 180 * angle / math.pi
        el_i = np.argmin(np.abs(np.arange(self.min_elevation, self.max_elevation, self.step_elevation) - elevation))
        A_atmos = self.atmospheric_attenuation[gs.id - len(satellites), el_i]
        A_atmos *= np.random.normal(1, 0.05)

        # free space path loss
        FSPL = 20 * math.log10(4 * math.pi * d * self.carrier_f * 1e9 / self.speed_of_light)  # db

        # noise
        T_sky = self.T_mr * (1 - 10 ** (-A_atmos / 10)) + 2.7 * 10 ** (-A_atmos / 10)
        P_noise = self.k * self.gsl_bandwidth * T_sky  # W
        P_noise *= np.random.normal(1, 0.02)

        # total receiver power
        P_rx = 10 ** ((self.EIRP - FSPL + self.G_rx - A_atmos) / 10)  # W

        # Shannon-Hartley
        return 1 if self.failed_gsl or gs.failed else self.gsl_bandwidth * math.log2(1 + P_rx / P_noise)

    def logging(self, file_path, current_time):
        data = {
            "time": current_time,
            "self_id": self.id,
            "position": (round(self.state.x, 4), round(self.state.y, 4), round(self.state.z, 4)),
            "neighbours": self.ISL_connections,
            "target_ids": self.target_ids,
            "generation_rate": round(self.generation_rate),
            "outgoing_throughputs": json.dumps({key: round(value) for key, value in self.outgoing_throughputs.items()}),
            "incoming_streams": json.dumps({key: round(sum(map(lambda x: x[1], value)))
                                            for key, value in self.incoming_streams.items()}),
            "outgoing_streams": json.dumps({key: round(sum(map(lambda x: x[1], value)))
                                            for key, value in self.outgoing_streams.items()}),
            "delay": round(self.delay, 2),
            "drop_rate": round(self.drop_rate, 2),
            "cost": round(self.cost, 2)
        }
        
        csv_row = ';'.join(str(data[key]) for key in data.keys())

        with open(file_path, "a") as file:
            file.write(csv_row + "\n")
