from decode_packets import decode_packets
from decode_survey_data import decode_survey_data
from decode_burst_data import decode_burst_data
from decode_status import decode_status
from plot_survey_data import plot_survey_data
from plot_burst_data import plot_burst_data
import random
import argparse
import os
import numpy as np
import pickle
import json

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

d = os.listdir(data_root)
tlm_files = [x for x in d if x.endswith('.tlm')]

print(f"found {len(tlm_files)} .tlm files")

work_dir = os.path.join(out_root,'in_progress')
if not os.path.exists(work_dir):
    os.makedirs(work_dir)


if len(tlm_files) > 0:

    raw_data = []
    packets = []

    # Decode packets from each TLM file, and tag the decoded
    # packet with its origin filename
    for fname in tlm_files:
        print(fname)
        with open(os.path.join(data_root, fname),'rb') as f:
            cur_data = np.fromfile(f,dtype='uint8')
            packets = decode_packets(cur_data, fname=fname)
            # with open("packets_" + fname[:-4] +".pkl","wb") as f:
            #     pickle.dump(packets, f)            

            # # print(list(filter(lambda packet: packet['dtype'] == 'S', packets)))


            # # packets.extend(decode_packets(cur_data, fname=fname))
            # packets = decode_packets(cur_data, fname=fname)
            # # sift out survey data
            S_data, unused_survey = decode_survey_data(packets)
            # # sift out burst data
            # plot_survey_data(S_data)



    # data = np.concatenate(raw_data).ravel()
    # print("loaded {0:2.1f} kB".format(len(data)/1024))

    # Decode the raw bytes into VPM packets
    # print('decoding packets...')
    # packets = decode_packets(data)

    # with open('packets.pkl','wb') as f:
    #     pickle.dump(packets, f)

    # outs = dict()
    # # Decode any survey data:
    # print("Decoding survey data")
    # S_data = decode_survey_data(packets)
    # outs['survey'] = S_data

    # # Decode any burst data:
    # print("Decoding burst data")
    # B_data = decode_burst_data(packets)
    # outs['burst'] = B_data

    # # Decode any status messages:
    # print("Decoding status messages")
    # stats = decode_status(packets)
    # outs['status'] = stats
    # with open('decoded_data.pkl','wb') as f:
    #     pickle.dump(outs,f)


    # # Plot that shit
    # plot_survey_data(S_data)
    # plot_burst_data(B_data)

