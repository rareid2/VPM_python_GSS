import numpy as np
import pickle
from scipy.io import loadmat
import os
import json

from process_packets import load_from_telemetry, save_packets_to_file_tree
from file_handlers import load_packets_from_tree
from data_handlers import decode_packets_TLM, decode_packets_CSV, decode_survey_data, unique_entries
from process_survey_data import save_survey_to_file_tree
from compute_ground_track import fill_missing_GPS_entries
from generate_survey_quicklooks import generate_survey_quicklooks

# CLEAR DB BEFORE RE-RUNNING THIS!!!!!
# following the steps to regenerate the database without messing with stuff

# need a database of EVERYTHING
data_root = '/Users/rileyannereid/macworkspace/test_data_VPM'
out_root = '/Users/rileyannereid/macworkspace/test_data_VPM/out'

# then use process packets
packets = load_from_telemetry(data_root)
save_packets_to_file_tree(packets, data_root, out_root)

# load packets from the file tree
packets = load_packets_from_tree(data_root + '/out')

# store S_data, use GPS func to get TLE info
S_data = []
fill_GPS = 1

if packets:
    from_packets, unused = decode_survey_data(packets, separation_time=4.5)
    S_data.extend(from_packets)

if S_data:

    # Replace any missing GPS positions with TLE-propagated data
    if fill_GPS:
        fill_missing_GPS_entries([x['GPS'][0] for x in S_data])

    save_survey_to_file_tree(S_data, out_root, file_types=['xml', 'mat'])

# next is to process burst data
# then add TX to survey plots 
# then generate some to check everything 
# I don't think I will calibrate the survey data.... 

# should hopefully be it for quicklooks
#generate_survey_quicklooks(data_root, out_root)