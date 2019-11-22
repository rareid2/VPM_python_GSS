from decode_packets import decode_packets
from decode_survey_data import decode_survey_data
from decode_burst_data import decode_burst_data_by_experiment_number, decode_burst_data_in_range, decode_burst_data_between_status_packets
from decode_status import decode_status
from plot_survey_data import plot_survey_data
from plot_burst_data import plot_burst_data
from file_handlers import write_burst_XML, write_survey_XML
from file_handlers import write_burst_netCDF, write_survey_netCDF
from packet_inspector import packet_inspector
import random
import argparse
import os
import numpy as np
import pickle
import shutil
import datetime
import dateutil
import logging



#  ----------- Parse input configuration -------------

parser = argparse.ArgumentParser(description="VPM Ground Support Software")
parser.add_argument("--in_dir",  required=False, type=str, default = None, help="path to directory of .tlm files")
parser.add_argument("--out_dir", required=False, type=str, default='output', help="path to output directory")
parser.add_argument("--workfile", required=False, type=str, default="in_progress.pkl", help="file to store unused packets (a pickle file)")
parser.add_argument("--previous_pkl_file", required=False, type=str, default=None, help="filename of previously-decoded packets (packets.pkl)")
parser.add_argument("--t1", action='append', help='burst packet start time. MM-DD-YYYYTHH:MM:SS', required=False)
parser.add_argument("--t2", action='append', help='burst packet stop time. MM-DD-YYYYTHH:MM:SS',  required=False)
parser.add_argument("--burst_cmd", required=False, type=str, default=None, help="Manually-assigned burst command, in hex; overrides any found commands")
parser.add_argument("--n_pulses", required=False, type=int, default=1, help="Manually-assigned burst_pulses; overrides any found commands")

g = parser.add_mutually_exclusive_group(required=False)
# g.add_argument("--save_xml", dest='do_xml', action='store_true', help="save decoded data in XML files")
g.add_argument("--no_xml", dest='do_xml', action='store_false', help="do not generate output XML files")
g.set_defaults(do_xml=True)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--save_pkl", dest='do_pickle', action='store_true', help="save decoded data as python Pickle files")
# g.add_argument("--no_pkl", dest='do_pickle',   action='store_false', help="do not generate output pickle files")
g.set_defaults(do_pickle=False)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--save_netcdf", dest='do_netcdf', action='store_true', help="save decoded data in netCDF files")
# g.add_argument("--no_netcdf", dest='do_netcdf', action='store_false', help="do not generate output netCDF files")
g.set_defaults(do_netcdf=False)

g = parser.add_mutually_exclusive_group(required=False)
# g.add_argument("--include_previous_data",dest='do_previous', action='store_true',  help="Load and include previously-decoded data, which was not processed")
g.add_argument("--ignore_previous_data", dest='do_previous', action='store_false', help="Do not include previously-decoded, but unprocessed data")
g.set_defaults(do_previous=True)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--move_completed", dest='move_completed', action='store_true', help="move completed .TLM files to the <out_dir>/processed")
g.set_defaults(move_completed=False)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--ignore_survey", dest='do_survey', action='store_false', help="Ignore any survey data")
g.set_defaults(do_survey=True)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--ignore_burst", dest='do_burst', action='store_false', help ="Ignore any burst data")
g.set_defaults(do_burst=True)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--debug", dest='debug', action='store_true', help ="Debug mode (extra chatty)")
g.set_defaults(debug=False)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--packet_inspector", dest='packet_inspector', action='store_true', help ="Show the packet inspector tool")
g.set_defaults(packet_inspector=False)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--interactive_plots", dest='int_plots', action='store_true', help ="Show plots interactively")
g.set_defaults(int_plots=False)

g = parser.add_mutually_exclusive_group(required=False)
g.add_argument("--identify_bursts_by_status_packets", dest='status_packets', action='store_true', help ="Identify burst experiments using status packets, which are sent before and after each burst")
g.set_defaults(status_packets=False)

args = parser.parse_args()
data_root = args.in_dir
out_root  = args.out_dir
in_progress_file = args.workfile


#  ----------- Check input directory -------------
if args.in_dir is not None:
    if not os.path.isdir(data_root):
        raise ValueError("Invalid input directory")

#  ----------- Check output directory ------------
if not os.path.exists(out_root):
    try:
        os.mkdir(out_root)
    except:
        raise ValueError("Failed to create output directory")

processed_dir = os.path.join(out_root,'processed')
if not os.path.exists(processed_dir):
    try:
        os.makedirs(processed_dir)
    except:
        raise ValueError("Invalid output directory")


#  ----------------- Start the logger ------------------
# log_filename = os.path.join(out_root, 'log.txt')
if args.debug:
    logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
else:
    logging.basicConfig(level=logging.INFO,  format='[%(name)s]\t%(levelname)s\t%(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

# Ignore divide-by-zero errors (which happen in plotting log-scaled spectrograms)
np.seterr(divide='ignore')

packets = []

# ------------------ Validate inputs --------------------

if args.burst_cmd:
    try:
        logging.info(f"using externally-assigned burst command 0x{args.burst_cmd}")
        burst_cmd = [int(x) for x in int(args.burst_cmd,16).to_bytes(3,'big')]
        burst_cmd = np.array(burst_cmd, dtype='uint8')
        logging.info(f"Burst command as ints = {burst_cmd}")
    except:
        raise ValueError("Cannot parse burst command ")
else:
    burst_cmd = None
# ---------- Load previously-decoded packets ------------
if args.previous_pkl_file is not None:
    with open(os.path.join(out_root,args.previous_pkl_file),'rb') as f:
        packets = pickle.load(f)

else:
# ------------------ Load TLM files -------------------
    d = os.listdir(data_root)

    tlm_files = [x for x in d if x.endswith('.tlm')]

    logging.info(f"found {len(tlm_files)} .tlm files")

    if len(tlm_files) > 0:        
        # Load packets from each TLM file, tag each with the 
        # source filename, and decode

        for fname in tlm_files:
            logging.info(f'Loading file {fname}')
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
                    logging.info(f'loaded {len(packets_in_progress)} in-progress packets')
                    packets.extend(packets_in_progress)

        

        # Save the decoded packets as an interstitial step 
        # (This isn't used anywhere, aside from module tests)
        with open(os.path.join(out_root,'packets.pkl'),'wb') as f:
            pickle.dump(packets, f)



# ----------------- Process any packets we have -------------
if packets:

    packets = sorted(packets, key = lambda p: p['header_timestamp'])

    # Run the packet inspector tool, if requested
    if args.packet_inspector:
        logging.info("Showing packet inspector for entire packet set")
        packet_inspector(packets)

    outs = dict()

    if args.do_burst:
        # Three different burst decoding methods to choose from:
        logging.info("Decoding burst data")
        if args.status_packets:
            # Decode by binning burst packets between two adjacent status packets,
            # which are automatically requested at the beginning and end of a burst
            logging.info(f'Processing bursts between status packets')
            B_data, unused_burst = decode_burst_data_between_status_packets(packets, debug_plots=args.packet_inspector)

        elif args.t1 and args.t2:
            # Manually bin burst packets between two timestamps
            t1 = dateutil.parser.parse(args.t1[0]).replace(tzinfo=datetime.timezone.utc)
            t2 = dateutil.parser.parse(args.t2[0]).replace(tzinfo=datetime.timezone.utc)
            logging.info(f'Processing bursts between {t1} and {t2}')
            B_data, unused_burst = decode_burst_data_in_range(packets,
                                   t1.timestamp(), t2.timestamp(),
                                   burst_cmd = burst_cmd, burst_pulses = args.n_pulses,
                                   debug_plots=args.packet_inspector)

        else:
            # Bin bursts by experiment number
            logging.info(f'Processing bursts by experiment number')
            B_data, unused_burst = decode_burst_data_by_experiment_number(packets, 
                                   burst_cmd = burst_cmd, burst_pulses = args.n_pulses,
                                   debug_plots=args.packet_inspector)
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


    # -------------- Store the output data -----------------
    # 1. as a Pickle file
    if args.do_pickle:
        with open(os.path.join(out_root,'decoded_data.pkl'),'wb') as f:
            pickle.dump(outs,f)

    # 2. as XML files
    if args.do_xml:
        if 'burst' in outs:
            logging.info("writing burst xml")
            write_burst_XML(outs['burst'], os.path.join(out_root,'burst_data.xml'))
        if 'survey' in outs:
            logging.info("writing survey xml")
            write_survey_XML(outs['survey'], os.path.join(out_root,'survey_data.xml'))

    # 3. as netCDF files
    if args.do_netcdf:
        if 'burst' in outs:
            logging.info("writing burst netCDF")
            write_burst_netCDF(outs['burst'], os.path.join(out_root,'burst_data.nc'))
        if 'survey' in outs:
            logging.info("writing survey netCDF")
            write_survey_netCDF(outs['survey'], os.path.join(out_root,'survey_data.nc'))

    # Write any status packets to a text file:
    if stats:
        logging.info("writing status messages")
        with open(os.path.join(out_root,'status_messages.txt'),'w') as f:
            for st in stats:
                f.write(st)

    # Plot the results!
    if args.do_burst and B_data:
        logging.info("plotting burst data")
        plot_burst_data(B_data, os.path.join(out_root,"burst_data.png"), show_plots = args.int_plots)

    if args.do_survey and S_data:
        logging.info("plotting survey data")
        plot_survey_data(S_data,os.path.join(out_root,"survey_data.png"), show_plots = args.int_plots)


else:
    logging.info("No packets loaded -- check input directory?")
