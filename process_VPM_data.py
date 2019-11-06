from decode_packets import decode_packets
from decode_survey_data import decode_survey_data
from decode_burst_data import decode_burst_data
from decode_status import decode_status
from plot_survey_data import plot_survey_data
from plot_burst_data import plot_burst_data
from file_handlers import write_burst_XML, write_survey_XML
import random
import argparse
import os
import numpy as np
import pickle
import shutil

from collections import defaultdict

parser = argparse.ArgumentParser(description="hey")
parser.add_argument("--in_dir",required=True, type=str, default = 'input', help="path to directory of .tlm files")
parser.add_argument("--out_dir", required=False, type=str, default='output', help="path to output directory")

args = parser.parse_args()

data_root = args.in_dir
out_root = args.out_dir


if not os.path.isdir(data_root):
    raise ValueError("Invalid input directory")

if not os.path.exists(out_root):
    os.mkdir(out_root)

# Where to store any temp files
work_dir = os.path.join(out_root,'in_progress')
if not os.path.exists(work_dir):
    os.makedirs(work_dir)

# Where to move the processed .TLM files
processed_dir = os.path.join(out_root,'processed')
if not os.path.exists(processed_dir):
    os.makedirs(processed_dir)

in_progress_file = os.path.join(work_dir, "in_progress.pkl")



d = os.listdir(data_root)

tlm_files = [x for x in d if x.endswith('.tlm')]

print(f"found {len(tlm_files)} .tlm files")

if len(tlm_files) > 0:

    raw_data = []
    packets = []

    all_S_data = []
    
    # Decode packets from each TLM file, and tag the decoded
    # packet with its origin filename

    for fname in tlm_files:
        print(fname)
        fpath = os.path.join(data_root, fname)
        with open(fpath,'rb') as f:
            cur_data = np.fromfile(f,dtype='uint8')
            # packets = decode_packets(cur_data, fname=fname)

            packets.extend(decode_packets(cur_data, fname=fname))

            # Move the original file to the "processed" directory
            # shutil.move(fpath, os.path.join(processed_dir,fname))

    
    # # Load any previously-unused packets, and add them to the list
    # if os.path.exists(in_progress_file):
    #     print("loading previous unused data")
    #     with open(in_progress_file,'rb') as f:
    #         packets_in_progress = pickle.load(f)    
    #     packets.extend(packets_in_progress)


    with open('packets.pkl','wb') as f:
        pickle.dump(packets, f)


    with open('packets.pkl','rb') as f:
        packets = pickle.load(f)


    outs = dict()

    print("Decoding burst data")
    B_data, unused_burst = decode_burst_data(packets)
    outs['burst'] = B_data

    print("Decoding survey data")
    S_data, unused_survey = decode_survey_data(packets)
    outs['survey'] = S_data

    print("Decoding status messages")
    stats = decode_status(packets)
    outs['status'] = stats


    if os.path.exists(in_progress_file):
        os.remove(in_progress_file)

    # Store any unused survey packets
    unused = unused_survey + unused_burst
    if unused:
        print(f"Storing {len(unused)} unused packets")
        with open(in_progress_file,'wb') as f:
            pickle.dump(unused, f)


    with open('decoded_data.pkl','wb') as f:
        pickle.dump(outs,f)

    print("writing burst xml")
    write_burst_XML(outs['burst'], os.path.join(out_root,'burst_data.xml'))
    print("writing survey xml")
    write_survey_XML(outs['survey'], os.path.join(out_root,'survey_data.xml'))
    # # Plot that shit
    # plot_survey_data(S_data)
    # plot_burst_data(B_data)

