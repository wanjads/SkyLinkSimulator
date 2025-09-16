import numpy as np
import itur
import h5py

attenuation_file_sat = "data/atmospheric_attenuation.npy"
min_elevation = 20  # in degrees
max_elevation = 90  # in degrees
step_elevation = 0.1

with h5py.File(f'data/positions/groundstation_positions/groundstation_positions.h5', 'r') as f_gs:
    dset_gs_pos = f_gs['positions'][0]
    num_groundstations = len(dset_gs_pos)

x = dset_gs_pos[:, 0]
y = dset_gs_pos[:, 1]
z = dset_gs_pos[:, 2]

long = np.degrees(np.arctan2(y, x))

# Calculate latitude (in degrees)
hyp = np.sqrt(x ** 2 + y ** 2)
lat = np.degrees(np.arctan2(z, hyp))

A_sat = []

# Link parameters
el = np.arange(min_elevation, max_elevation, step_elevation)
n_el = len(el)
f_sat = 19
f_gs = 28.5
D = 1  # Receiver antenna diameter of 1 m
p = 5

for i in range(num_groundstations):
    A_sat.append(itur.atmospheric_attenuation_slant_path(lat[i], long[i], f_sat, el, p, D).value)
    print(f'Ground Station {i+1} / {num_groundstations}')


with open(attenuation_file_sat, "wb") as file:
    np.save(file, np.array(A_sat))

print("saved all atmospheric attenuation files")