import math
import numpy as np


class State:

    def __init__(self, long, lat, x, y, z):

        self.long = long
        self.lat = lat
        self.x = x
        self.y = y
        self.z = z

    def as_vector(self):
        return np.array([self.long, self.lat])

    def as_normalized_vector(self):
        return np.array([math.cos(math.pi * self.long / 180), math.sin(math.pi * self.long / 180), self.lat / 90])

    def distance_to(self, other):
        return np.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)
