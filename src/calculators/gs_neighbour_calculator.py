import numpy as np
import h5py
from cosmicbeats import CosmicBeats

# Define the CosmicBeats object
config_file = "CosmicBeats/configs/oneweb/config.json"
cosmicbeats = CosmicBeats(config_file)
satellites = cosmicbeats.get_satellite_list()
groundstations = cosmicbeats.get_groundstation_list()

# Define parameters
num_satellites = len(satellites)
earth_radius_m = 6371000.0  # Earth's radius in meters
time_interval_sec = 15
total_days = 7
total_seconds = total_days * 24 * 60 * 60
num_timepoints = total_seconds // time_interval_sec
max_timepoints_per_file = 1000  # Define max time points per file


def calculate_distances_from_center(positions):
    # Calculate distances from the center of the Earth
    distances_from_center = np.linalg.norm(positions, axis=1)
    return distances_from_center


def can_see_groundstations(sat_distances, sat_positions, gs_positions):
    h = sat_distances - earth_radius_m
    term1 = np.sqrt((earth_radius_m + h) ** 2 - earth_radius_m ** 2)[:, np.newaxis]
    distance_matrix = np.linalg.norm(sat_positions[:, np.newaxis, :] - gs_positions[np.newaxis, :, :], axis=-1)
    visibility_matrix = term1 > distance_matrix

    visible_groundstations = []
    for i in range(visibility_matrix.shape[0]):
        visible = np.where(visibility_matrix[i])[0].tolist()
        visible_groundstations.append(visible)
    return [[gs + 636 for gs in l] for l in visible_groundstations]


# Satellite visibility calculation
file_index = 0
time_counter = 0

while time_counter < num_timepoints:
    num_timepoints_in_file = min(max_timepoints_per_file, num_timepoints - time_counter)

    with h5py.File(f'../../data/visibility/groundstation_visibility/satellite_visibility_groundstations_{file_index}.h5', 'w') as f_vis:

        # Load ground station positions
        with h5py.File(f'../../data/positions/groundstation_positions/groundstation_positions.h5', 'r') as f_gs:
            dset_gs_pos = f_gs['positions'][:]
            num_groundstations = dset_gs_pos.shape[1]

            # Load existing satellite positions
            with h5py.File(f'../../data/positions/satellite_positions/satellite_positions_{file_index}.h5', 'r') as f_pos:
                dset_sat_pos = f_pos['positions']

                # Variable-length storage for visibility
                dt = h5py.special_dtype(vlen=np.dtype('int32'))
                dset_vis = f_vis.create_dataset('visibility',
                                                shape=(num_timepoints_in_file, num_satellites),
                                                dtype=dt,
                                                compression="gzip")  # Add compression

                # Iterate over time points and calculate visibility
                for t in range(num_timepoints_in_file):
                    sat_positions = dset_sat_pos[t, :, :]
                    gs_positions = dset_gs_pos[0, :, :]
                    sat_distances = calculate_distances_from_center(sat_positions)
                    dset_vis[t] = can_see_groundstations(sat_distances, sat_positions, gs_positions)

                    if (time_counter + t + 1) % 1 == 0:
                        print(f"Progress: {time_counter + t + 1}/{num_timepoints} time points processed.")

    time_counter += num_timepoints_in_file
    file_index += 1

print("All groundstation visibility data has been successfully saved.")
