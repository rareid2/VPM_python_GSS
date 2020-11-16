import numpy as np
import pickle
from scipy.io import loadmat
import os
import json

from process_packets import load_from_telemetry, save_packets_to_file_tree
from file_handlers import load_packets_from_tree, read_burst_XML
from data_handlers import decode_packets_TLM, decode_packets_CSV, decode_survey_data, unique_entries, decode_burst_data_between_status_packets
from process_survey_data import save_survey_to_file_tree
from compute_ground_track import fill_missing_GPS_entries
from generate_survey_quicklooks import generate_survey_quicklooks
from process_burst_data import save_burst_to_file_tree, gen_burst_plots

# CLEAR DB BEFORE RE-RUNNING THIS!!!!!
# following the steps to regenerate the database without messing with stuff

# need a database of EVERYTHING
data_root = '/Users/rileyannereid/macworkspace/test_data_VPM'
out_root = '/Users/rileyannereid/macworkspace/test_data_VPM/out'

fill_GPS = 1

# then use process packets
packets = load_from_telemetry(data_root)
save_packets_to_file_tree(packets, data_root, out_root)

# load packets from the file tree
packets = load_packets_from_tree(data_root + '/out')

# -------------------------- SURVEY ------------------------------
# store S_data, use GPS func to get TLE info
S_data = []

if packets:
    from_packets, unused = decode_survey_data(packets, separation_time=4.5)
    S_data.extend(from_packets)

if S_data:

    # Replace any missing GPS positions with TLE-propagated data
    if fill_GPS:
        fill_missing_GPS_entries([x['GPS'][0] for x in S_data])

    save_survey_to_file_tree(S_data, out_root, file_types=['xml', 'mat'])

# should be it for quicklooks
generate_survey_quicklooks(data_root, out_root)

# -------------------------- BURST ------------------------------
# re-open the burst files and add cal data and change the filter to on/off and gain to high/low

# see what bursts are in the 
check_for_bursts = data_root + '/burst_data/'
for root, dirs, files in os.walk(check_for_bursts):
    bursts_to_do = []
    for fname in files:
        if 'burst' in fname and fname.endswith('.xml'):
            bursts_to_do.append(os.path.join(check_for_bursts, fname))

burst_data = [read_burst_XML(burst_file) for burst_file in bursts_to_do]

# correct the uBBr calibration inputs
E_cal = 1e6/(1.1*82*10*32768) # to get from raw to uV/m

for b in burst_data:
    b = b[0]
    del b['bbr_config']['E_CAL']
    del b['bbr_config']['B_CAL']
    del b['bbr_config']['B_GAIN']
    del b['bbr_config']['B_FILT']

    if b['bbr_config']['E_GAIN'] == 1:
        del b['bbr_config']['E_GAIN']
        b['GAIN'] = 'high'
        b['CAL'] = E_cal
    else:
        del b['bbr_config']['E_GAIN']
        b['GAIN'] = 'low'
        b['CAL'] = E_cal * 10

    if b['bbr_config']['E_FILT'] == 1:
        del b['bbr_config']['E_FILT']
        b['FILT'] = 'off'
    else:
        del b['bbr_config']['E_FILT']
        b['FILT'] = 'on'

    if fill_GPS:
        fill_missing_GPS_entries(b['G'])

# 'regenerate' the burst files (not from raw, but from prev xml and add in the updated info)
save_burst_to_file_tree(burst_data, out_root, filetypes=['xml','mat'])
gen_burst_plots(burst_data, data_root + '/burst_fig/')