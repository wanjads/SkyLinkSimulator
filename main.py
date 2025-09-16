import concurrent.futures
import heapq
import pickle
import random
import h5py
import numpy as np
import argparse
from src.strategies.references.bentpipe import BentPipe
from src.strategies.references.dijkstra import Dijkstra
from src.strategies.references.gounder import Gounder
from src.strategies.references.random import Random
from src.strategies.references.q_learning import QLearning
from src.strategies.ucb.tile_coded_ucb import TileCodedUCB
from src.strategies.ucb.ucb import UCB
from src.utils import Time
from src.groundstation import Groundstation
from src.paketmanager import PaketManager
from src.satellite import Satellite
from scipy.spatial import KDTree

# DOUBLE CHECK, IF THESE PARAMETERS MATCH THE ONES USED BY COSMICBEATS WHEN CALCULATING POSITIONS/VISIBILITY/...

TIME_STEPS_PER_FILE = 1000
NUM_SATELLITES = 636
NUM_GROUNDSTATIONS = 146
ANTENNAS_PER_GROUNDSTATION = 8
TIME_DELTA = 15
START_TIME = "2023-09-28 08:26:00"
FAILURE_TIME = "2023-09-30 08:26:00"
RESET_TIME = "2023-10-02 08:26:00"
GSL_FAILURE_SHARE = 0.03
ISL_FAILURE_SHARE = 0.50
GS_FAILURES = False
GS_FAILURE_SHARE = 0.50
PRINT_EVERY_X_TIME_STEP = 60


def set_seed(seed=0):
    random.seed(seed)
    np.random.seed(seed)


def save_evaluation_data(eps, tim, avg_delay, drop_rate, cost, gen_rate, tp, avg_h, main_link_output, file):
    data = {
        'episode': eps,
        'time': tim,
        'avg_delay': avg_delay,
        'drop_rate': drop_rate,
        'generation_rate': gen_rate,
        'throughput': tp,
        'avg_hops': avg_h,
        'main_link_out': main_link_output,
        'cost': cost
    }

    with open(file, 'ab') as f:
        pickle.dump(data, f)


def assign_positions_to_satellites(satellites, earth_coordinate_positions):
    satellite_positions = [np.array((sat.state.x, sat.state.y, sat.state.z)) for sat in satellites]

    tree = KDTree(satellite_positions)

    for p in earth_coordinate_positions:
        _, index = tree.query((p[2], p[3], p[4]))
        satellites[index].data_generator.satellites_grid_points += [(p[0], p[1])]


def gsl_failures_satellites(current_time, failed_satellite_ids):

    if current_time.to_str() == FAILURE_TIME:
        print("NETWORK FAILURE")
        failed_satellite_ids = random.sample(range(NUM_SATELLITES), k=int(NUM_SATELLITES * GSL_FAILURE_SHARE))
        return failed_satellite_ids

    elif current_time.to_str() == RESET_TIME:

        print("NETWORK FIXED")
        return []

    else:
        return failed_satellite_ids


def isl_failures_satellites(current_time, failed_satellite_ids):

    if current_time.to_str() == FAILURE_TIME:
        print("NETWORK FAILURE")
        failed_satellite_ids = random.sample(range(NUM_SATELLITES), k=int(NUM_SATELLITES * ISL_FAILURE_SHARE))
        return failed_satellite_ids

    elif current_time.to_str() == RESET_TIME:

        print("NETWORK FIXED")
        return []

    else:
        return failed_satellite_ids


def network_failure_groundstations(current_time, failed_groundstation_ids):
    if current_time.to_str() == FAILURE_TIME:
        print("NETWORK FAILURE")
        failed_groundstation_ids = random.sample(range(NUM_SATELLITES, NUM_SATELLITES + NUM_GROUNDSTATIONS),
                                                 k=int(NUM_GROUNDSTATIONS * GS_FAILURE_SHARE))
        return failed_groundstation_ids

    elif current_time.to_str() == RESET_TIME:
        print("NETWORK FIXED")
        return []

    else:
        return failed_groundstation_ids


def update_groundstations(groundstations, satellites):
    for sat in satellites:
        sat.GSL_connections = []

    closest_satellites = {}

    for gs in groundstations:
        closest_satellites[gs.id] = []

    for sat in satellites:
        for gs_id in sat.visible_groundstations:
            gs = groundstations[gs_id - NUM_SATELLITES]
            distance = gs.state.distance_to(sat.state)
            heapq.heappush(closest_satellites[gs_id], (-distance, sat.id))

    for gs in closest_satellites:
        closest_satellites[gs].sort(key=lambda x: -x[0])

    for gs in closest_satellites:
        gsls = 0
        for dist, sat_id in closest_satellites[gs]:
            if gsls < ANTENNAS_PER_GROUNDSTATION:
                satellites[sat_id].GSL_connections += [gs]
                gsls += 1


def network_init():
    print("INITIALIZATION")

    # initialize groundstations
    print("init groundstations")
    groundstations = [Groundstation(gs_id) for gs_id in range(NUM_SATELLITES, NUM_SATELLITES + NUM_GROUNDSTATIONS)]
    with h5py.File(f'data/positions/groundstation_positions/groundstation_positions.h5', 'r') as p:
        dset = p['positions']
        gs_index = 0
        for groundstation in groundstations:
            groundstation.state_update(*dset[0, gs_index, :])
            gs_index += 1

    # initialize satellites
    print("init satellites")
    atmospheric_attenuation = np.load("data/atmospheric_attenuation.npy")
    Satellite.atmospheric_attenuation = atmospheric_attenuation
    satellites = [Satellite(sat_id) for sat_id in range(NUM_SATELLITES)]

    # initialize the paket manager
    print("init paket manager")
    paket_manager = PaketManager(satellites, groundstations)

    return satellites, groundstations, paket_manager


def run(strategy, rep_no, growth_factor=1, gsl_failures=False, isl_failures=False, max_time_steps=7 * 24 * 60 * 4,
        logging=False, seed=0):

    set_seed(seed)

    satellites, groundstations, paket_manager = network_init()

    if logging:
        with open("logging/old/log_groundstations.csv", "a") as file:
            file.write("time; "
                       "id; "
                       "position; "
                       "outgoing_throughput; "
                       "incoming_streams; "
                       "outgoing_streams; "
                       "delay; "
                       "drop_rate "
                       "\n")
        with open("logging/old/log_satellites.csv", "a") as file:
            file.write("time; "
                       "id; "
                       "position; "
                       "neighbours; "
                       "target_ids; "
                       "generation_rate; "
                       "outgoing_throughputs; "
                       "incoming_streams; "
                       "outgoing_streams; "
                       "delay; "
                       "drop_rate; "
                       "cost \n")

    current_time = Time().from_str(START_TIME)
    step = 0
    file_index = 0
    failed_gsls_satellite_ids = []
    failed_isls_satellite_ids = []
    failed_gs_ids = []

    while step < max_time_steps:
        if step % PRINT_EVERY_X_TIME_STEP == 0:
            print(f"({strategy.strategy_name}) current time: {current_time}")

        if isl_failures:
            failed_isls_satellite_ids = isl_failures_satellites(current_time, failed_isls_satellite_ids)
            for sat in satellites:
                sat.failed_isl = (sat.id in failed_isls_satellite_ids)

        if gsl_failures:
            failed_gsls_satellite_ids = gsl_failures_satellites(current_time, failed_gsls_satellite_ids)
            for sat in satellites:
                sat.failed_gsl = (sat.id in failed_gsls_satellite_ids)

        if GS_FAILURES:
            failed_gs_ids = network_failure_groundstations(current_time, failed_gs_ids)
            for gs in groundstations:
                gs.failed = (gs.id in failed_gs_ids)

        with (h5py.File(f'data/grid/grid_{file_index}.h5', 'r') as sv,
              h5py.File(f'data/visibility/groundstation_visibility/satellite_visibility_groundstations_{file_index}.h5',
                        'r') as gsv):
            dset_sv = sv['visibility'][step % TIME_STEPS_PER_FILE]
            dset_gsv = gsv['visibility'][step % TIME_STEPS_PER_FILE]
            for s in satellites:
                s.ISL_connections = dset_sv[s.id]
                s.visible_groundstations = dset_gsv[s.id]

        with h5py.File(f'data/positions/satellite_positions/satellite_positions_{file_index}.h5', 'r') as p:
            dset = p['positions']
            for satellite in satellites:
                satellite.state_update(*dset[step % TIME_STEPS_PER_FILE, satellite.id, :])

        with h5py.File(f'data/data_generation/satellite_data_generation_{file_index}.h5', 'r') as g:
            dset = g['data_generation'][step % TIME_STEPS_PER_FILE]
            for satellite in satellites:
                satellite.update_generation_rate(dset, growth_factor=growth_factor)

        for sat in satellites:
            sat.target_ids = []
        update_groundstations(groundstations, satellites)
        strategy.set_targets(satellites, groundstations, current_time)

        for sat in satellites:
            sat.update_outgoing_throughput(groundstations, satellites)

        paket_manager.set_rewards()
        strategy.learn(satellites, groundstations, current_time)

        if logging:
            for gs in groundstations:
                gs.logging("logging/log_groundstations.csv", current_time.to_str())
            for sat in satellites:
                sat.logging("logging/log_satellites.csv", current_time.to_str())

        avg_delay = (sum(list(map(lambda n: n.generation_rate * (1 - n.drop_rate) * n.delay, satellites))) /
                     sum(list(map(lambda n: n.generation_rate * (1 - n.drop_rate), satellites))))

        drop_rate = (sum(list(map(lambda n: n.generation_rate * n.drop_rate,
                                  satellites))) /
                     sum(list(map(lambda n: n.generation_rate, satellites))))

        cost = (sum(list(map(lambda n: n.generation_rate * n.cost, satellites))) /
                sum(list(map(lambda n: n.generation_rate, satellites))))

        generation_rate = sum(list(map(lambda n: n.generation_rate, satellites)))

        throughput = (1 - drop_rate) * generation_rate

        average_hops = paket_manager.get_average_hops()

        satellites_with_outgoing_traffic = list(filter(lambda n: sum(list(
            map(lambda streams: sum(list(map(lambda stream: stream[1], streams))),
                n.outgoing_streams.values()))) > 0, satellites))
        main_link_out_share = \
            (np.mean(list(
                map(lambda n: sum(list(map(lambda stream: stream[1], n.outgoing_streams[n.target_ids[0]]))) /
                              sum(list(map(lambda streams: sum(list(map(lambda stream: stream[1], streams))),
                                           n.outgoing_streams.values()))),
                    satellites_with_outgoing_traffic))))

        save_evaluation_data(step, current_time.to_str(), avg_delay, drop_rate, cost, generation_rate,
                             throughput, average_hops, main_link_out_share,
                             file="results/evaluation_data_"
                                  + strategy.strategy_name + "_"
                                  + str(int(gsl_failures)) + "_"
                                  + str(int(isl_failures)) + "_"
                                  f"{growth_factor:.1f}_"
                                  + str(rep_no) +
                                  ".npy")

        step += 1
        if step % TIME_STEPS_PER_FILE == 0:
            file_index += 1
        current_time = current_time.add_seconds(TIME_DELTA)


def main():
    parser = argparse.ArgumentParser(description="Run strategies with specified parameters.")

    parser.add_argument("--growth_factor", type=float, default=2, help="Factor to scale data generation rate.")
    parser.add_argument("--gsl_failures", type=bool, default=False, help="Enable gsl failures (True/False).")
    parser.add_argument("--isl_failures", type=bool, default=False, help="Enable isl failures (True/False).")
    parser.add_argument("--max_time_steps", type=int, default=4*60, help="Maximum time steps to run.")
    parser.add_argument("--logging", type=bool, default=False, help="Enable logging (True/False).")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for reproducibility.")
    parser.add_argument("--repetitions", type=int, default=1, help="Number of repetitions for each strategy.")

    args = parser.parse_args()

    strategies = [
        Random(),
        BentPipe(),
        Dijkstra(),
        Gounder(),
        UCB(),
        QLearning(alpha=0.15, gamma=0.90, epsilon=0.15),
        TileCodedUCB(['distance'], 5e5, 2)
    ]

    debug = False
    if debug:
        run(UCB(),0, 2, False, False, 4*60, False, 0)
    else:
        with (concurrent.futures.ProcessPoolExecutor(max_workers=min(61, 4 * len(strategies) * args.repetitions))
              as executor):
            futures = []
            for rep_no in range(args.repetitions):
                for gf in [2]:
                    for strategy_index, strategy in enumerate(strategies):
                        futures.append(
                            executor.submit(
                                run,
                                strategy,
                                rep_no,
                                growth_factor=gf,
                                gsl_failures=args.gsl_failures,
                                isl_failures=args.isl_failures,
                                max_time_steps=args.max_time_steps,
                                logging=args.logging,
                                seed=args.seed + rep_no
                            )
                        )

            concurrent.futures.wait(futures)

            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    import traceback
                    print(f"[FAIL] in worker execution: {e}")
                    traceback.print_exc()


if __name__ == "__main__":
    main()
