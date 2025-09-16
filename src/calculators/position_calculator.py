import copy
import numpy as np
import h5py
from cosmicbeats import CosmicBeats

config_file = "CosmicBeats/configs/oneweb/config.json"

cosmicbeats = CosmicBeats(config_file)
satellites = cosmicbeats.get_satellite_list()

# Define parameters
num_satellites = len(satellites)
time_interval_sec = 15
total_days = 7

# Calculate the number of time points
total_seconds = 26000*15 + 15000  # total_days * 24 * 60 * 60
num_timepoints = total_seconds // time_interval_sec
max_timepoints_per_file = 1000  # Define max time points per file


def calculate_satellite_positions(time):
    return np.array([s.get_Position(time).to_tuple() for s in satellites])


# Create multiple HDF5 files and datasets
file_index = 26
time_counter = 26000
current_time = copy.deepcopy(cosmicbeats.start_time)
current_time = current_time.add_seconds(cosmicbeats.time_delta * time_counter)

while time_counter < num_timepoints:
    with h5py.File(f'../../data/positions/satellite_positions/satellite_positions_{file_index}.h5', 'w') as f:
        dset = f.create_dataset('positions',
                                shape=(min(max_timepoints_per_file, num_timepoints - time_counter), num_satellites, 3),
                                dtype='float64',
                                compression="gzip")  # Add compression

        for t in range(min(max_timepoints_per_file, num_timepoints - time_counter)):
            positions = calculate_satellite_positions(current_time)
            dset[t, :, :] = positions
            if (t + time_counter) % 10 == 0:
                print(f"Progress: {t + time_counter}/{num_timepoints} time points processed.")
            current_time = current_time.add_seconds(cosmicbeats.time_delta)

        time_counter += max_timepoints_per_file
        print("Saved file no " + str(file_index))
        file_index += 1

print("All data has been successfully saved.")
