from CosmicBeats.src.sim.simulator import Simulator
from CosmicBeats.src.nodes.inode import ENodeType
from CosmicBeats.src.models.imodel import EModelTag


class CosmicBeats:

    def __init__(self, config_file):
        filepath = config_file
        print("setup simulator")
        self.sim = Simulator(filepath)
        self.topology = self.sim.get_Topologies()[0]

        self.start_time = self.sim.get_SimStartTime()
        self.end_time = self.sim.get_SimEndTime()

        self.no_of_sim_steps = int(self.sim.get_SimEnv()[1])
        self.time_delta = self.sim.get_SimEnv()[2]

    def get_satellite_list(self):
        topology = self.sim.get_SimEnv()[0][0]
        return topology.get_NodesOfAType(ENodeType.SAT)

    def get_groundstation_list(self):
        topology = self.sim.get_SimEnv()[0][0]
        return topology.get_NodesOfAType(ENodeType.GS)

    def get_groundstation_passes(self, node):
        satellite_list = self.get_groundstation_list()
        orbit_model = node.has_ModelWithTag(EModelTag.ORBITAL)

        passes = []
        for gs in satellite_list:
            passes += [(gs.nodeID, orbit_model.call_APIs("get_Passes",
                                                         _gs=gs,
                                                         _start=self.start_time,
                                                         _end=self.end_time,
                                                         _minElevation=0))]

        neighbours = []
        for p in passes:
            if len(p[1]) > 0:
                neighbours += [p]

        return neighbours

    def get_node(self, node_id):
        return self.topology.get_Node(node_id)
