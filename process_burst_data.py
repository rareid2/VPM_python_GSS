import sys
import os
import datetime
import pickle
import gzip
from scipy.io import savemat
from configparser import ConfigParser
import numpy as np
from file_handlers import load_packets_from_tree
from file_handlers import read_burst_XML, write_burst_XML
from data_handlers import decode_status, decode_uBBR_command, decode_burst_command, process_burst
from db_handlers import get_packets_within_range
from log_handlers import get_last_access_time, log_access_time
from cli_plots import plot_burst_data, plot_burst_map

import matplotlib.pyplot as plt
import logging


def process_bursts_from_database(packet_db, t1=None, t2=None, date_added=None):
    logger = logging.getLogger('process_bursts_from_database')

    I_packets = get_packets_within_range(packet_db, dtype='I',t1=t1, t2=t2, date_added=date_added)
    print(f'Found {len(I_packets)} status packets')

    # Select only "burst" status packets
    I_packets = list(filter(lambda p: chr(p['data'][3])=='B', I_packets))
    I_packets = sorted(I_packets, key = lambda p: p['header_timestamp']) 
    logger.debug(f'loaded {len(I_packets)} burst headers')
    stats = decode_status(I_packets)

    completed_bursts = []
    # logger.info(f'I_packets has length {len(I_packets)} pre-sift')
    for IA, IB in zip(stats[0:-1], stats[1:]):
        # Timestamps for each status packet. Add a little buffer, in case
        # the tagging was weird or the packetizer stuck a few packets after it.
        ta = datetime.datetime.utcfromtimestamp(IA['header_timestamp'] - 1.5)
        tb = datetime.datetime.utcfromtimestamp(IB['header_timestamp'] + 1.5)

        # Confirm that the burst command is the same within each status packet:        
        IA_cmd = IA['prev_burst_command']
        IB_cmd = IB['prev_burst_command']
        
        # Status packets don't belong to the same burst
        if any(IA_cmd!=IB_cmd):
            logger.debug(f'command mismatch between status packets')
            continue
        # Too much time between packets
        if (tb - ta) > datetime.timedelta(days=2):
            logger.debug(f'timedelta too long {tb - ta}')
            continue
        # System was reset in between status packets; not a valid burst
        if(IA['uptime'] > IB['uptime']):
            logger.debug('uptime order')
            continue


        # print(f'{ta} -- {tb} (dt = {tb - ta})')
        E_packets = get_packets_within_range(packet_db, dtype='E', t1 = ta, t2 = tb)
        B_packets = get_packets_within_range(packet_db, dtype='B', t1 = ta, t2 = tb)
        G_packets = get_packets_within_range(packet_db, dtype='G', t1 = ta, t2 = tb)
        
        # Skip if there's no data to process
        if not E_packets and not B_packets and not G_packets:
            logger.debug('No data found!')
            continue
        logger.info(f'burst between {ta} and {tb} (dt = {tb - ta})')
        logger.info(f'loaded {len(E_packets)} E packets, {len(B_packets)} B packets, and {len(G_packets)} GPS packets')
        
        avail_exp_nums = np.unique([x['exp_num'] for x in (E_packets + B_packets + G_packets)])
        
        logger.debug(f'Available experiment nums: {avail_exp_nums}')
        
        for e_num in avail_exp_nums:
            
            # Check echo'd command in the GPS packet
            for gg in filter(lambda p: p['exp_num'] == e_num, G_packets):
                if gg['start_ind'] ==0:
                    cmd_gps = np.flip(gg['data'][0:3])
                    logger.debug(f'gps command: {cmd_gps}')
                    if (IA_cmd != cmd_gps).any():
                        logger.warning("GPS and status command echo mismatch")
            
            
            # Get burst configuration parameters:
            burst_config = decode_burst_command(IA_cmd)
            burst_config['burst_pulses'] = IA['burst_pulses']

            logger.debug(f'burst configuration: {burst_config}')

            packets_to_process = list(filter(lambda p: p['exp_num'] == e_num, E_packets + B_packets + G_packets))
            processed = process_burst(packets_to_process, burst_config)
            # processed['I'] = [IA, IB]
            processed['status'] = [IA, IB]
            processed['bbr_config'] = decode_uBBR_command(processed['status'][0]['prev_bbr_command'])
            processed['header_timestamp'] = ta.replace(tzinfo=datetime.timezone.utc).timestamp()
            processed['experiment_number'] = e_num
            
            completed_bursts.append(processed)

    logger.info(f'decoded {len(completed_bursts)} bursts')
    return completed_bursts



def save_burst_to_file_tree(burst_data, out_root, filetypes):
    
    logger = logging.getLogger('save_burst_to_file_tree')
    for ftype in filetypes:
        if ftype not in ['xml','mat','pkl']:
            logger.warning(f'unsupported file type: {ftype}')
            continue
        
        for b in burst_data:
            print(b['header_timestamp'])
            d = datetime.datetime.utcfromtimestamp(b['header_timestamp'])
    #         t = datetime.datetime.utcfromtimestamp(b['header_timestamp'])
            outpath = os.path.join(out_root,ftype,f'{d.year}', '{:02d}'.format(d.month),'{:02d}'.format(d.day))
        
            if b['config']['TD_FD_SELECT'] == 0:
                mode = 'FD'
            else:
                mode = 'TD'
            filename = f'VPM_burst_{mode}_' + d.strftime('%Y-%m-%d_%H%M') +'.' + ftype
            

            outfile = os.path.join(outpath, filename)

            if not os.path.exists(outpath):
                logger.info(f'making directory {outpath}')
                os.makedirs(outpath)
            if os.path.isfile(outfile):
                logger.debug(f'file exists: {outfile}')
                expand = 1
                while True:
                    expand += 1
                    new_file_name = outfile.split(f'.{ftype}')[0] + '_' + str(expand) + f'.{ftype}'
                    if os.path.isfile(new_file_name):
                        continue
                    else:
                        outfile = new_file_name
                        break

            print(f'writing {outfile}')
            
            if ftype =='xml':
                write_burst_XML([b], outfile)

            if ftype=='mat':
                savemat(outfile, {'burst_data' : b})

            if ftype=='pkl':
                with open(outfile,'wb') as file:
                    pickle.dump(b, file)


def gen_burst_plots(bursts, out_root, do_plots=True, do_maps=True,
    dpi=150, cal_file=None,TX_file=None, TLE_file=None):

    logger = logging.getLogger('gen_burst_plots')
       
    ftype = 'png'

    for b in bursts:
        d = datetime.datetime.utcfromtimestamp(b['header_timestamp'])
#         t = datetime.datetime.utcfromtimestamp(b['header_timestamp'])
        outpath = os.path.join(out_root,'figures',f'{d.year}', '{:02d}'.format(d.month),'{:02d}'.format(d.day))
    
        if b['config']['TD_FD_SELECT'] == 0:
            mode = 'FD'
        else:
            mode = 'TD'
        filename = f'VPM_burst_{mode}_' + d.strftime('%Y-%m-%d_%H%M') +'.' + ftype
        

        outfile = os.path.join(outpath, filename)

        if not os.path.exists(outpath):
            logger.info(f'making directory {outpath}')
            os.makedirs(outpath)
        if os.path.isfile(outfile):
            logger.debug(f'file exists: {outfile}')
            expand = 1
            while True:
                expand += 1
                new_file_name = outfile.split(f'.{ftype}')[0] + '_' + str(expand) + f'.{ftype}'
                if os.path.isfile(new_file_name):
                    continue
                else:
                    outfile = new_file_name
                    break

        if do_plots:
            plot_burst_data([b], show_plots=False, filename=outfile, dpi=dpi)
        if do_maps:
            filename = f'VP_map_' + d.strftime('%Y-%m-%d_%H%M') +'.' + ftype
            outfile = os.path.join(outpath, filename)
            plot_burst_map([b],show_plots=False, filename=outfile, dpi=dpi,
                        TLE_file=TLE_file, TX_file=TX_file)
def main():

    # -------- Load configuration file --------
    config = ConfigParser()
    fp = open('GSS_settings.conf')
    config.read_file(fp)
    fp.close()

    # -------- Configure logger ---------
    logfile = config['logging']['log_file']
    logging.basicConfig(level=eval(f"logging.{config['logging']['log_level']}"),
             filename = logfile, 
             format='[%(asctime)s]\t%(module)s.%(name)s\t%(levelname)s\t%(message)s',
             datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    np.seterr(divide='ignore')

    # -------- Load some settings -------
    packet_db = config['db_locations']['packet_db_file']
    out_root = config['db_locations']['burst_tree_root']
    file_types = config['burst_config']['file_types']
    file_types = [x.strip() for x in file_types.split(',')]

    do_plots = config['burst_config']['do_plots']
    do_maps  = config['burst_config']['do_maps']
    cal_file = config['burst_config']['calibration_file']
    dpi = int(config['burst_config']['dpi'])

    TLE_file = config['burst_config']['TLE_file'].strip()
    TX_file  = config['burst_config']['TX_file'].strip()
    access_log = config['logging']['access_log'].strip()


    last_timestamp = get_last_access_time(access_log,'process_burst_data')
    last_time = datetime.datetime.utcfromtimestamp(last_timestamp)
    t1 = datetime.datetime(2020,5,1,0,0,0)
    t2 = datetime.datetime(2020,5,4,0,0,0)
    logging.info(f'Last run time: {last_time} UTC')

    bursts = process_bursts_from_database(packet_db, t1 = t1, t2=t2, date_added=last_time)

    if do_plots or do_maps:
        gen_burst_plots(bursts, out_root, do_plots=do_plots,
                 do_maps=do_maps, dpi=dpi, cal_file=cal_file,
                 TLE_file=TLE_file, TX_file=TX_file)

    # Save output files    
    save_burst_to_file_tree(bursts, out_root, file_types)

    # Success!
    log_access_time(access_log,'process_burst_data')

if __name__ == "__main__":
    main()