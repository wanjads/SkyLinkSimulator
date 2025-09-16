import copy
from collections import deque


class PaketManager:

    def __init__(self, satellites, groundstations):
        self.satellites = satellites
        self.groundstations = groundstations

        self.TTL = 200  # 1000  # (60000) in ms
        self.max_number_of_groundstation_connections = 1000
        self.speed_of_light = 299792.458  # m / ms

    def set_rewards(self):

        # backup actions
        actions = {}
        for s in self.satellites:
            actions[s] = copy.deepcopy(s.target_ids)

        # set new update indicators
        for s in self.satellites:
            s.buffer_was_updated = 0
            s.traffic_left = 0
            s.delay_was_updated = False
            s.drop_rate_was_updated = False

        for gs in self.groundstations:
            gs.drop_rate_was_updated = False

        # update streams
        self.update_streams()

        # update buffers
        for sat in self.satellites:
            sat.update_buffer(self.satellites, self.groundstations)

        for gs in self.groundstations:
            gs.update_buffer()

        # update drop rates
        self.update_drop_rates()

        # update local drop rates
        for sat in self.satellites:
            self.update_local_drop_rate(sat)

        # update delays
        for gs in self.groundstations:
            gs.update_delay()

        self.update_delays()

        # set costs
        for s in self.satellites:
            if s.delay >= self.TTL:
                s.drop_rate = 1
                s.delay = self.TTL
            s.cost = s.drop_rate * self.TTL + (1 - s.drop_rate) * s.delay

        # reinstantiate actions
        for s in self.satellites:
            s.target_ids = actions[s]

    def update_streams(self):

        # set incoming and outgoing traffic to 0
        for s in self.satellites:
            s.drop_rate = 0
            s.incoming_streams = {}
            s.outgoing_streams = {}
            s.drops_per_link = []

        for gs in self.groundstations:
            gs.drop_rate = 0
            gs.incoming_streams = {}
            gs.outgoing_streams = {}

        # fill outgoing links
        for sat in self.satellites:
            if sat.generation_rate > 0:
                sat.incoming_streams["generation"] = [[[sat.id], sat.generation_rate]]

        queue = deque([s.id for s in self.satellites])
        kill_counter = 0

        while len(queue) > 0:
            if kill_counter > 100000:
                break

            nodeID = queue.popleft()

            if nodeID < len(self.satellites):
                node = self.satellites[nodeID]
            else:
                node = self.groundstations[nodeID - len(self.satellites)]

            remaining_streams = []
            for incoming_node in node.incoming_streams:
                remaining_streams += node.incoming_streams[incoming_node]

            if nodeID < len(self.satellites):
                for target in node.target_ids:
                    if target < len(self.satellites):
                        target_node = self.satellites[target]
                    else:
                        target_node = self.groundstations[target - len(self.satellites)]

                    if nodeID in target_node.incoming_streams:
                        old_streams = target_node.incoming_streams[nodeID]
                    else:
                        old_streams = []

                    if len(remaining_streams) > 0:
                        target_outgoing_streams = [stream for stream in remaining_streams if target not in stream[0]]
                        remaining_traffic = sum(stream[1] for stream in target_outgoing_streams)

                        if remaining_traffic == 0:
                            break

                        if target >= len(self.satellites):
                            capacity = 0.9 * node.gsl_capacity(self.groundstations[target - len(self.satellites)],
                                                               self.satellites)
                        else:
                            capacity = 0.9 * node.isl_capacity(node.state.distance_to(self.satellites[target].state))

                        link_capacity = node.outgoing_throughputs[target]
                        new_traffic = min(min(link_capacity, capacity), remaining_traffic)
                        share_transmitted_new_traffic = new_traffic / remaining_traffic
                        share_cc_estimate = min(1, capacity / remaining_traffic)

                        new_streams = []
                        for out_stream in target_outgoing_streams:
                            kill_counter += 1
                            new_streams.append(
                                [out_stream[0] + [target], share_transmitted_new_traffic * out_stream[1]])
                            remaining_streams.remove(out_stream)
                            if share_cc_estimate < 1:
                                remaining_streams.append([out_stream[0], (1 - share_cc_estimate) * out_stream[1]])

                        target_node.incoming_streams[nodeID] = new_streams
                        node.outgoing_streams[target] = new_streams

                        if new_streams != old_streams and new_traffic >= 1 and target not in queue:
                            queue.append(target)

            else:
                remaining_traffic = sum(stream[1] for stream in remaining_streams)
                new_traffic = min(node.outgoing_throughput, remaining_traffic)
                new_streams = []
                for out_stream in remaining_streams:
                    share = new_traffic / remaining_traffic
                    new_streams.append([out_stream[0] + ["core"], share * out_stream[1]])
                node.outgoing_streams["core"] = new_streams

    def update_drop_rates(self):

        delivered_rates_pre_satellite = {sat.id: 0 for sat in self.satellites}
        for gs in self.groundstations:
            if "core" in gs.outgoing_streams:
                for stream in gs.outgoing_streams["core"]:
                    delivered_rates_pre_satellite[stream[0][0]] += stream[1]

        for satellite in self.satellites:
            if "generation" in satellite.incoming_streams:
                generation_rate = satellite.incoming_streams["generation"][0][1]
            else:
                generation_rate = 0

            satellite.drop_rate = 0 if generation_rate == 0 else (1 - delivered_rates_pre_satellite[satellite.id] /
                                                                  generation_rate)

    @staticmethod
    def update_local_drop_rate(satellite):

        incoming_data = sum(list(map(lambda all_streams_from_source: sum(list(map(lambda stream: stream[1],
                                                                                  all_streams_from_source))),
                                     satellite.incoming_streams.values())))
        if incoming_data > 0:
            outgoing_data = sum(list(map(lambda all_streams_to_target: sum(list(map(lambda stream: stream[1],
                                                                                    all_streams_to_target))),
                                         satellite.outgoing_streams.values())))
            satellite.local_drop_rate = 1 - outgoing_data / incoming_data
        else:
            satellite.local_drop_rate = 0

        satellite.incoming_data = incoming_data

    def update_delays(self):

        streams_per_satellite = {sat.id: [] for sat in self.satellites}
        for gs in self.groundstations:
            if "core" in gs.outgoing_streams:
                for stream in gs.outgoing_streams["core"]:
                    if stream[0][0] in streams_per_satellite:
                        streams_per_satellite[stream[0][0]].append(stream)

        for satellite in self.satellites:
            if "generation" in satellite.incoming_streams:
                generation_rate = satellite.incoming_streams["generation"][0][1]
            else:
                generation_rate = 0

            delay = 0
            streams_per_outgoing_link = {}
            for stream in streams_per_satellite[satellite.id]:
                path = stream[0]
                traffic = stream[1]
                stream_delay = 0

                if path[-1] == "core":
                    for nodeID in path[:-1]:
                        if nodeID < len(self.satellites):
                            current_node = self.satellites[nodeID]
                        else:
                            current_node = self.groundstations[nodeID - len(self.satellites)]

                        if current_node.buffer_level > 0:
                            outgoing_traffic = sum(s[1] for ss in current_node.outgoing_streams.values() for s in ss)
                            queuing_delay = current_node.buffer_level / outgoing_traffic if outgoing_traffic > 0 else 0
                        else:
                            queuing_delay = 0

                        stream_delay += queuing_delay

                    for i in range(len(path) - 2):
                        current = path[i]
                        target = path[i + 1]

                        if current < len(self.satellites):
                            current_node = self.satellites[current]
                        else:
                            current_node = self.groundstations[current - len(self.satellites)]

                        if target < len(self.satellites):
                            target_node = self.satellites[target]
                        else:
                            target_node = self.groundstations[target - len(self.satellites)]

                        dist = current_node.state.distance_to(target_node.state)

                        stream_delay += dist / self.speed_of_light
                else:
                    stream_delay = self.TTL

                outgoing_link = stream[0][1]
                if outgoing_link not in streams_per_outgoing_link:
                    streams_per_outgoing_link[outgoing_link] = []

                streams_per_outgoing_link[outgoing_link].append([traffic, stream_delay])

                delay += (traffic * stream_delay) / generation_rate if generation_rate > 0 else 0

            delays_per_outgoing_link = {}
            for outgoing_link in satellite.target_ids:
                if outgoing_link in streams_per_outgoing_link:
                    total_weighted_delay = sum(
                        traffic * delay for traffic, delay in streams_per_outgoing_link[outgoing_link])
                    total_traffic = sum(traffic for traffic, delay in streams_per_outgoing_link[outgoing_link])
                    delays_per_outgoing_link[outgoing_link] = total_weighted_delay / total_traffic
                else:
                    delays_per_outgoing_link[outgoing_link] = self.TTL

            satellite.delay = delay
            satellite.delays_per_outgoing_link = delays_per_outgoing_link

    def get_average_hops(self):

        delivered_rate = 0
        weighted_hops = 0
        for gs in self.groundstations:
            if "core" in gs.outgoing_streams:
                streams = gs.outgoing_streams["core"]
                if len(streams) > 0:
                    weighted_hops += sum(map(lambda s: (len(s[0]) - 2) * s[1], streams))
                    delivered_rate += sum(map(lambda s: s[1], streams))

        if delivered_rate > 0:
            return weighted_hops / delivered_rate

        return 0
