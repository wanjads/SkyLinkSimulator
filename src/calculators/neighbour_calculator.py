import h5py
import numpy as np
from cosmicbeats import CosmicBeats

# Define the CosmicBeats object
config_file = "CosmicBeats/configs/oneweb/config.json"
cosmicbeats = CosmicBeats(config_file)
start_time = cosmicbeats.sim.get_SimStartTime()
end_time = cosmicbeats.sim.get_SimEndTime()
satellites = cosmicbeats.get_satellite_list()

# Define parameters
num_satellites = len(satellites)
earth_radius_m = 6371000.0  # Earth's radius in meters
time_interval_sec = 15
total_days = 7
total_seconds = total_days * 24 * 60 * 60
num_timepoints = total_seconds // time_interval_sec
max_timepoints_per_file = 1000  # Define max time points per file


def neighbours(dist_matrix):

    effective_distances = 4000000
    vis_matrix = effective_distances > dist_matrix

    visible_satellites = []
    for i in range(vis_matrix.shape[0]):
        visible = np.where(vis_matrix[i])[0].tolist()
        visible_satellites.append([j for j in visible if j != i])

    return visible_satellites


file_index = 0
time_counter = 0

while time_counter < num_timepoints:
    num_timepoints_in_file = min(max_timepoints_per_file, num_timepoints - time_counter)

    with (h5py.File(f'../../data/positions/satellite_positions/satellite_positions_{file_index}.h5', 'r') as f_pos):

        dset_pos = f_pos['positions']
        with h5py.File(f'../../data/grid/grid_{file_index}.h5', 'w') as grid_file:
            dt = h5py.special_dtype(vlen=np.dtype('int32'))
            dset_vis = grid_file.create_dataset('visibility',
                                                shape=(num_timepoints_in_file, num_satellites),
                                                dtype=dt,
                                                compression="gzip")
            for t in range(num_timepoints_in_file):
                positions = dset_pos[t, :, :]
                distance_matrix = np.linalg.norm(positions[:, np.newaxis, :] - positions[np.newaxis, :, :],
                                                 axis=-1)
                visibility_matrix = neighbours(distance_matrix)
                connection_matrix = [[] for sat_id in range(num_satellites)]
                no_of_connections = [0 for sat_id in range(num_satellites)]
                for sat_id in range(len(visibility_matrix)):
                    x, y, z = positions[sat_id]
                    sat_long = np.degrees(np.arctan2(y, x))
                    sat_lat = np.degrees(np.arctan2(z, np.sqrt(x ** 2 + y ** 2)))
                    nbs = visibility_matrix[sat_id]
                    min_dist_north = np.inf
                    min_dist_south = np.inf
                    min_dist_east = np.inf
                    min_dist_west = np.inf
                    for n_id in nbs:
                        x, y, z = positions[n_id]
                        n_long = np.degrees(np.arctan2(y, x))
                        n_lat = np.degrees(np.arctan2(z, np.sqrt(x ** 2 + y ** 2)))
                        if 90 > sat_lat + 14 > n_lat > sat_lat and sat_long - 5 < n_long < sat_long + 5:
                            dist = distance_matrix[sat_id][n_id]
                            if dist < min_dist_north:
                                n_north = n_id
                                min_dist_north = dist
                        elif -90 < sat_lat - 14 < n_lat < sat_lat and sat_long - 5 < n_long < sat_long + 5:
                            dist = distance_matrix[sat_id][n_id]
                            if dist < min_dist_south:
                                n_south = n_id
                                min_dist_south = dist
                        elif (sat_lat - 5 < n_lat < sat_lat and sat_long - 16 < n_long < sat_long
                                or sat_long < -174 and sat_long + 346 < n_long < sat_long + 360):
                            dist = distance_matrix[sat_id][n_id]
                            if dist < min_dist_west:
                                n_west = n_id
                                min_dist_west = dist
                        elif (sat_lat - 5 < n_lat < sat_lat and sat_long < n_long < sat_long + 16
                                or sat_long > 174 and sat_long - 360 < n_long < sat_long - 346):
                            dist = distance_matrix[sat_id][n_id]
                            if dist < min_dist_east:
                                n_east = n_id
                                min_dist_east = dist
                    if (min_dist_north < np.inf
                            and n_north not in connection_matrix[sat_id]
                            and no_of_connections[n_north] < 4
                            and no_of_connections[sat_id] < 4):
                        connection_matrix[sat_id] += [n_north]
                        connection_matrix[n_north] += [sat_id]
                        no_of_connections[sat_id] += 1
                        no_of_connections[n_north] += 1
                    if (min_dist_south < np.inf
                            and n_south not in connection_matrix[sat_id]
                            and no_of_connections[n_south] < 4
                            and no_of_connections[sat_id] < 4):
                        connection_matrix[sat_id] += [n_south]
                        connection_matrix[n_south] += [sat_id]
                        no_of_connections[sat_id] += 1
                        no_of_connections[n_south] += 1
                    if (min_dist_west < np.inf
                            and n_west not in connection_matrix[sat_id]
                            and no_of_connections[n_west] < 4
                            and no_of_connections[sat_id] < 4):
                        connection_matrix[sat_id] += [n_west]
                        connection_matrix[n_west] += [sat_id]
                        no_of_connections[sat_id] += 1
                        no_of_connections[n_west] += 1
                    if (min_dist_east < np.inf
                            and n_east not in connection_matrix[sat_id]
                            and no_of_connections[n_east] < 4
                            and no_of_connections[sat_id] < 4):
                        connection_matrix[sat_id] += [n_east]
                        connection_matrix[n_east] += [sat_id]
                        no_of_connections[sat_id] += 1
                        no_of_connections[n_east] += 1

                dset_vis[t] = connection_matrix

                if (time_counter + t + 1) % 10 == 0:
                    print(f"Progress: {time_counter + t + 1}/{num_timepoints} time points processed.")

    time_counter += num_timepoints_in_file
    file_index += 1

print("All visibility data has been successfully saved.")
