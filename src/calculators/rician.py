import math
import numpy as np
from scipy.stats import rv_continuous


class Rician(rv_continuous):

    def __init__(self):
        super().__init__()

        self.a = 0

        # see Latency versus Reliability in LEO Mega Constellations by pan et al.
        self.be = 10 ** 1.5
        self.o = self.be
        self.m = 2
        self.alpha = math.pow(2 * self.be * self.m / (2 * self.be * self.m + self.o), self.m) / (2 * self.be)
        self.beta = 1 / (2 * self.be)
        self.delta = self.o / ((2 * self.be) * (2 * self.be * self.m + self.o))

        self.c0 = 1
        self.c1 = self.delta

        self.lambda_dash = 794328234724.2822

    def _pdf(self, x, *args):
        return self.alpha * (self.c0 / self.lambda_dash
                             * math.exp(-((self.beta - self.delta) / self.lambda_dash) * x)
                             + self.c1 / self.lambda_dash ** 2
                             * x
                             * math.exp(-((self.beta - self.delta) / self.lambda_dash) * x))


# Instantiate the Rician distribution
rician_dist = Rician()

# Generate the large number of samples
large_samples = []
for i in range(100):
    large_samples.extend(rician_dist.rvs(size=int(1e4)))
    print(i)

# Save the samples to a file
np.save('../data/rician_samples/rician_samples.npy', large_samples)
