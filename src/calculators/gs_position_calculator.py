import copy
import numpy as np
import h5py
from cosmicbeats import CosmicBeats

config_file = "CosmicBeats/configs/oneweb/config.json"

cosmicbeats = CosmicBeats(config_file)
groundstations = cosmicbeats.get_groundstation_list()

# Define parameters
num_groundstations = len(groundstations)
time_interval_sec = 15
total_days = 7

# Calculate the number of time points
total_seconds = total_days * 24 * 60 * 60
num_timepoints = total_seconds // time_interval_sec
max_timepoints_per_file = 1000  # Define max time points per file


def calculate_groundstation_positions(time):
    return np.array([gs.get_Position(time).to_tuple() for gs in groundstations])


# Create multiple HDF5 files and datasets
file_index = 0
time_counter = 0
current_time = copy.deepcopy(cosmicbeats.start_time)

with h5py.File(f'../../data/positions/groundstation_positions/groundstation_positions.h5', 'w') as f:
    dset = f.create_dataset('positions',
                            shape=(1, num_groundstations, 3),
                            dtype='float64',
                            compression="gzip")  # Add compression

    positions = calculate_groundstation_positions(current_time)
    dset[0, :, :] = positions

print("All data has been successfully saved.")
