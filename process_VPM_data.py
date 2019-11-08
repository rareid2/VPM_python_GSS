from decode_packets import decode_packets
from decode_survey_data import decode_survey_data
from decode_burst_data import decode_burst_data_by_experiment_number
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

import logging


#  ----------- Start the logger -------------

logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)
# logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s', "%Y-%m-%d %H:%M:%S") 
# # Log file handler
# fh = logging.FileHandler('log_filename.txt')
# fh.setLevel(logging.DEBUG)
# fh.setFormatter(formatter)
# logger.addHandler(fh)

# # Log console handler
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# ch.setFormatter(formatter)
# logger.addHandler(ch)# logger.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

#  ----------- Parse input configuration -------------

parser = argparse.ArgumentParser(description="hey")
parser.add_argument("--in_dir",required=True, type=str, default = 'input', help="path to directory of .tlm files")
parser.add_argument("--out_dir", required=False, type=str, default='output', help="path to output directory")
parser.add_argument("--workfile", required=False, type=str, default="in_progress.pkl", help="file to store unused packets (a pickle file)")
parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--save_xml", dest='do_xml', action='store_true')
parser.add_argument("--no_xml", dest='do_xml', action='store_false')
parser.set_defaults(do_xml=True)
parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--save_pkl", dest='do_pickle', action='store_true')
parser.add_argument("--no_pkl", dest='do_pickle', action='store_false')
parser.set_defaults(do_pickle=True)
parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--use_previous_data",    dest='do_previous', action='store_true')
parser.add_argument("--ignore_previous_data", dest='do_previous', action='store_false')
parser.set_defaults(do_previous=True)
parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--move_completed", dest='move_completed', action='store_true')
parser.set_defaults(move_completed=False)
parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--ignore_survey", dest='do_survey', action='store_false')
parser.set_defaults(do_survey=True)
parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--ignore_burst", dest='do_burst', action='store_false')
parser.set_defaults(do_burst=True)


args = parser.parse_args()

data_root = args.in_dir
out_root  = args.out_dir

in_progress_file = args.workfile


if not os.path.isdir(data_root):
    raise ValueError("Invalid input directory")

if not os.path.exists(out_root):
    os.mkdir(out_root)

# Where to move the processed .TLM files
processed_dir = os.path.join(out_root,'processed')
if not os.path.exists(processed_dir):
    try:
        os.makedirs(processed_dir)
    except:
        raise ValueError("Invalid output directory")



# ------------------ Load TLM files -------------------
d = os.listdir(data_root)

tlm_files = [x for x in d if x.endswith('.tlm')]

logging.info(f"found {len(tlm_files)} .tlm files")

if len(tlm_files) > 0:

    raw_data = []
    packets = []

    all_S_data = []
    
    # Decode packets from each TLM file, and tag the decoded
    # packet with its origin filename

    for fname in tlm_files:
        logging.info(fname)
        fpath = os.path.join(data_root, fname)
        with open(fpath,'rb') as f:
            cur_data = np.fromfile(f,dtype='uint8')
            
            packets.extend(decode_packets(cur_data, fname=fname))
            
            # Move the original file to the "processed" directory
            if args.move_completed:
                shutil.move(fpath, os.path.join(processed_dir,fname))

    
    # Load any previously-unused packets, and add them to the list
    if args.do_previous:
        if os.path.exists(in_progress_file):
            logging.info("loading previous unused data")
            with open(in_progress_file,'rb') as f:
                packets_in_progress = pickle.load(f)    
            packets.extend(packets_in_progress)


    # Save the decoded packets as an interstitial step
    with open(os.path.join(out_root,'packets.pkl'),'wb') as f:
        pickle.dump(packets, f)

    # with open(os.path.join(out_root,'packets.pkl'),'rb') as f:
    #     packets = pickle.load(f)

    outs = dict()

    if args.do_burst:
        logging.info("Decoding burst data")
        B_data, unused_burst = decode_burst_data_by_experiment_number(packets)
        outs['burst'] = B_data

    if args.do_survey:
        logging.info("Decoding survey data")
        S_data, unused_survey = decode_survey_data(packets)
        outs['survey'] = S_data

    logging.info("Decoding status messages")
    stats = decode_status(packets)
    outs['status'] = stats

    # Delete previous unused packet file -- they've either
    # been processed by this point, or are in the new unused list
    if args.do_previous:
        if os.path.exists(in_progress_file):
            os.remove(in_progress_file)

        # Store any unused survey packets
        unused = unused_survey + unused_burst

        if unused:
            logging.info(f"Storing {len(unused)} unused packets")
            with open(in_progress_file,'wb') as f:
                pickle.dump(unused, f)


    # Store the output data:
    # 1. as a Pickle file
    if args.do_pickle:
        with open(os.path.join(out_root,'decoded_data.pkl'),'wb') as f:
            pickle.dump(outs,f)

    # 2. as XML files
    if args.do_xml:
        logging.info("writing burst xml")
        write_burst_XML(outs['burst'], os.path.join(out_root,'burst_data.xml'))
        logging.info("writing survey xml")
        write_survey_XML(outs['survey'], os.path.join(out_root,'survey_data.xml'))
    
    # Plot the results!
    if args.do_burst and B_data:
        logging.info("plotting survey data")
        plot_burst_data(B_data, os.path.join(out_root,"burst_data.png"))

    if args.do_survey and S_data:
        logging.info("plotting burst data")
        plot_survey_data(S_data,os.path.join(out_root,"survey_data.png"))
    
