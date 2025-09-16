import math
import os
from astropy.coordinates import EarthLocation
import numpy as np
import h5py
import datetime
import pickle
from scipy.spatial import KDTree
from cosmicbeats import CosmicBeats

# Define the CosmicBeats object
config_file = "CosmicBeats/configs/oneweb/config.json"
cosmicbeats = CosmicBeats(config_file)
satellites = cosmicbeats.get_satellite_list()

# Define parameters
num_satellites = len(satellites)
time_interval_sec = 15
total_days = 7
total_seconds = total_days * 24 * 60 * 60
num_timepoints = total_seconds // time_interval_sec
max_timepoints_per_file = 1000  # Define max time points per file

# Load population data
population_data_path = "../../data/population/gpw_v4_population_count_rev11_2020_1_deg.asc"
population = np.loadtxt(population_data_path, skiprows=6)
population[population == -9999] = 0  # Replace no-data values

# Load earth coordinate positions from a previously saved file
file_path = '../../data/earth_coordinate_positions.pkl'
if os.path.exists(file_path):
    with open(file_path, 'rb') as file:
        earth_coordinate_positions = pickle.load(file)
else:
    earth_coordinate_positions = []
    for lat in range(-89, 91, 1):
        for lon in range(-179, 181, 1):
            if population[-lat + 89][lon + 179] > 0:
                earthLoc = EarthLocation.from_geodetic(lon=lon, lat=lat, height=0, ellipsoid='WGS84').get_itrs()
                x = float(earthLoc.x.value)
                y = float(earthLoc.y.value)
                z = float(earthLoc.z.value)
                earth_coordinate_positions += [(lat, lon, x, y, z)]
                print("calculated earth coordinate positions: ", lat, lon)
    with open(file_path, 'wb') as file:
        pickle.dump(earth_coordinate_positions, file)


# Function to convert UTC time to local time based on longitude
def utc_to_local(utc, longitude):
    offset = int((longitude + 180) / 15) - 12
    local_time = utc + datetime.timedelta(hours=offset)
    return local_time


# Function to calculate data traffic based on local time and population
def estimate_uplink_traffic(sat_grid_points, utc, longitude):
    local_time = utc_to_local(utc, longitude)
    hour = local_time.hour
    usage_factors = np.array([24 / 199 * hour for hour in [7.0, 6.0, 5.5,
                                                           5.0, 5.0, 5.5,
                                                           6.0, 6.5, 7.5,
                                                           8.0, 8.5, 8.5,
                                                           9.0, 9.0, 9.0,
                                                           9.5, 10.0, 10.5,
                                                           10.5, 11.0, 11.0,
                                                           11.0, 10.5, 9.0
                                                           ]])
    usage_factor = usage_factors[hour]

    devices_per_person = 0.0015875  # expected no of users in Jan. 26
    average_data_usage_per_second = 22976  # bps
    total_population = sum([population[-gp[0] + 89, gp[1] + 179] for gp in sat_grid_points])
    total_traffic = total_population * devices_per_person * average_data_usage_per_second * usage_factor
    return total_traffic


def assign_positions_to_satellites(position_tree, sats, coordinate_positions):
    earth_positions_per_sat = [[] for _ in range(len(sats))]
    for p in coordinate_positions:
        _, index = position_tree.query((p[2], p[3], p[4]))
        earth_positions_per_sat[index].append([p[0], p[1]])
    return earth_positions_per_sat


def long_from_pos(position):
    return math.degrees(math.atan2(position[1], position[0]))


# Satellite data generation calculation
file_index = 0
time_counter = 0

while time_counter < num_timepoints:
    num_timepoints_in_file = min(max_timepoints_per_file, num_timepoints - time_counter)

    with (h5py.File(f'../../data/positions/satellite_positions/satellite_positions_{file_index}.h5', 'r') as f_pos,
          h5py.File(f'../../data/data_generation/satellite_data_generation_{file_index}.h5', 'w') as f_data):
        dset_pos = f_pos['positions']
        dset_data = f_data.create_dataset('data_generation',
                                          shape=(num_timepoints_in_file, num_satellites),
                                          dtype='float64',
                                          compression="gzip")

        for t in range(num_timepoints_in_file):
            utc_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=(time_counter + t) * time_interval_sec)
            positions = dset_pos[t, :, :]
            tree = KDTree(positions)

            # Assign earth grid points to satellites
            earth_positions_per_satellite = assign_positions_to_satellites(tree, satellites, earth_coordinate_positions)

            # Calculate data generation
            data_generation = [estimate_uplink_traffic(earth_positions_per_satellite[int((sat.nodeID - 1) / 2)],
                                                       utc_time, long_from_pos(positions[int((sat.nodeID - 1) / 2)]))
                               for sat in satellites]
            dset_data[t] = np.array(data_generation, dtype='float64')

            if (time_counter + t + 1) % 10 == 0:
                print(f"Progress: {time_counter + t + 1}/{num_timepoints} time points processed.")

    time_counter += num_timepoints_in_file
    file_index += 1

print("All data generation data has been successfully saved.")
