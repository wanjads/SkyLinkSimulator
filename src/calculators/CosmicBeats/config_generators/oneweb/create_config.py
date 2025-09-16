"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

This is a quick script to generate the configuration file for the IoT application
Usage: python3 create_config.py tle_file gs_file start_time end_time delta output_file 
I assume a 3LE file. 
I assume a GS file with lat, long. 
I assume start_time and end_time are YYYY-MM-DD HH:MM:SS
"""

# The tles can be found at: The tles can be found from:
#    https://celestrak.org/NORAD/elements/gp.php?GROUP=planet&FORMAT=tle
# The current gs locations are approximated from:
#    Kiruthika Devaraj, Ryan Kingsbury, Matt Ligon, Joseph Breu, Vivek
#    Vittaldev, Bryan Klofas, Patrick Yeon, and Kyle Colton. Dove High
#    Speed Downlink System. In Small Satellite Conference, 2017.
# and also:
#    Transmitting, Fast and Slow: Scheduling Satellite Traffic through Space and Time
#    Bill Tao, Maleeha Masood, Indranil Gupta, Deepak Vasisht
#    MobiCom 2023
    
# The power numbers are all converted numbers from:
#    Orbital Edge Computing: Nanosatellite Constellations as a New Class of Computing System
#    Bradley Denby and Brandon Lucia
#    ASPLOS 2020

# The radio numbers are all from:
#   Kiruthika Devaraj, Matt Ligon, Eric Blossom, Joseph Breu, Bryan Klofas, 
#   Kyle Colton, and Ryan Kingsbury. Planet High Speed Radio: 
#   Crossing Gbps from a 3U Cubesat. In Small Satellite Conference, 2019.
    

import os

def get_satellite_string(node_id, tle_line_1, tle_line_2):
    string = """
                {
                    "type": "SAT",
                    "iname": "SatelliteBasic",
                    "nodeid": %d,
                    "loglevel": "error",
                    "tle_1": "%s", 
                    "tle_2": "%s",
                    "additionalargs": "",
                    "models":[
                        {
                            "iname": "ModelOrbit"
                        },
                        {
                            "iname": "ModelFovTimeBased",
                            "min_elevation": 5,
                            "tol": 10000
                        }
                    ]
                }""" % (node_id, tle_line_1, tle_line_2)
                
    return string


def get_groundstation_string(node_id, gs_lat, gs_lon):
    string = """
                {
                    "type": "GS",
                    "iname": "GSBasic",
                    "nodeid": %d,
                    "loglevel": "error",
                    "latitude": %f,
                    "longitude": %f,
                    "elevation": 0.0,
                    "additionalargs": "",
                    "models":[
                        {
                            "iname": "ModelFovTimeBased",
                            "min_elevation": 0,
                            "tol": 0
                        }
                    ]
                }""" % (node_id, gs_lat, gs_lon)
    return string


if __name__ == "__main__":

    # Usage: python3 create_iot_config.py tle_file gs_file start_time end_time delta output_file

    tle_file = "../oneweb/oneweb.tle"
    gs_file = "gs_file.txt"
    start_time = "2023-09-28 08:26:00"
    end_time = "2023-10-05 08:26:00"  # "2023-09-28 09:26:00"
    delta = 15
    
    output_file = open("../../configs/oneweb/config.json", "w+")
    
    base_str = """
{
    "topologies":
    [
        {
            "name": "Oneweb",
            "id": 0,
            "nodes":
            [
    """
    output_file.write(base_str)
    
    # add tle nodes
    node_id = 0
    
    with open(tle_file, "r") as f:
        lines = f.readlines()
        for i in range(0, len(lines), 3):
            line = lines[i:i+3]
            node_id += 1
            tle_line_1 = line[1][:-1]
            tle_line_2 = line[2][:-1]  # Ignore the newlines
            output_file.write(get_satellite_string(node_id, tle_line_1, tle_line_2))
            output_file.write(",\n")
            node_id += 1
            
    # add groundstations

    with open(gs_file, "r") as f:
        for line in f:
            gs_lat = float(line.split(",")[0])
            gs_lon = float(line.split(",")[1])
            output_file.write(get_groundstation_string(node_id, gs_lat, gs_lon))
            output_file.write(",\n")
            
            node_id += 1            
            
    # remove last comma
    output_file.seek(output_file.tell() - 3, os.SEEK_SET)
    output_file.truncate()

    # add end of file
    end_str = """
                ]
            }
        ],
        "simtime":
        {
            "starttime": "%s",
            "endtime": "%s",
            "delta": %s
        },
        "simlogsetup":
        {
            "loghandler": "LoggerFileChunkwise",
            "logfolder": "onewebLogs",
            "logchunksize": 1000000000000
        }
}
    """ % (start_time, end_time, delta)

    output_file.write(end_str)
    output_file.close()
