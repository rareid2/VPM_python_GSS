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


def process_bursts_from_database(packet_db, t1=None, t2=None, date_added=None, max_lookback_time=datetime.timedelta(hours=2)):
    ''' Decode bursts from the packet database, between header timestamps t1 and t2.
        if date_added is provided, only do packets added after date_added.
        First, we search for completed bursts, with a header and a footer status packet.
        Any lone packets will be treated as a footer packet, since typically the data
        is missing the header only. In this case, we'll injest any packets between the
        footer timestamp, and max_lookback_time previous.
    '''
    logger = logging.getLogger('process_bursts_from_database')

    I_packets = get_packets_within_range(packet_db, dtype='I',t1=t1, t2=t2, date_added=date_added)

    if not I_packets:
        return []

    # Select only "burst" status packets
    I_packets = list(filter(lambda p: chr(p['data'][3])=='B', I_packets))
    I_packets = sorted(I_packets, key = lambda p: p['header_timestamp']) 
    logger.debug(f'loaded {len(I_packets)} burst headers')

    stats = decode_status(I_packets)
    pairs = []

    # Loop through status packets to identify possible bursts:
    while stats:
        # Get the current footer
        IB = stats.pop()
        tb = IB['header_timestamp']
        
        # Is there a candidate header?
        if stats:
            IA = stats[-1]
            ta = IA['header_timestamp']
            dt = datetime.timedelta(seconds = tb - ta)
            
            # Confirm the packets aren't too far apart
            if dt < max_lookback_time:
                
                # Confirm that the burst command is the same within both status packets:        
                if all(IA['prev_burst_command']==IB['prev_burst_command']):
                    
                    # Confirm the payload wasn't reset in between the two packets:
                    if(IA['uptime'] < IB['uptime']):
                        logger.info('Header / Footer pair found')
                        IA = stats.pop()
                        pairs.append([IA, IB])
                        continue
                    else:
                        logger.debug('uptime order; skipping')
                else:
                    logger.debug(f'command mismatch between status packets; skipping')  
            else:
                logger.debug(f'Max lookback time exceeded')
        
        # If all else fails, this is a lone footer packet.
        logger.info('Single footer found')
        pairs.append([None, IB])
        
    logger.info(f'Have {len(pairs)} sets to check')

    completed_bursts = []

    # Process packets between each set of headers:
    for index, (IA, IB) in enumerate(pairs):
        logger.debug(f'doing {index}')
        
        tb = datetime.datetime.fromtimestamp(round(IB['header_timestamp']) + 1, tz=datetime.timezone.utc)
        if not IA:
            ta = tb - max_lookback_time
        else:
            ta = datetime.datetime.fromtimestamp(round(IA['header_timestamp']) - 1, tz=datetime.timezone.utc)
        
        
        
        # Load the rest of the packets within the time interval
        statcheck = get_packets_within_range(packet_db, dtype='I', t1 = ta, t2 = tb)
        E_packets = get_packets_within_range(packet_db, dtype='E', t1 = ta, t2 = tb)
        B_packets = get_packets_within_range(packet_db, dtype='B', t1 = ta, t2 = tb)
        G_packets = get_packets_within_range(packet_db, dtype='G', t1 = ta, t2 = tb)

        # Skip if there's no data to process
        if not E_packets and not B_packets and not G_packets:
            logger.debug('No data found!')
            continue

        logger.info(f'burst between {ta} and {tb} (dt = {tb - ta})')
        logger.info(f'loaded {len(E_packets)} E packets, {len(B_packets)} B packets, {len(G_packets)} GPS packets, and {len(statcheck)} status packets')

        avail_exp_nums = np.unique([x['exp_num'] for x in (E_packets + B_packets + G_packets)])

        logger.debug(f'Available experiment nums: {avail_exp_nums}')


        for e_num in avail_exp_nums:
            try:
                # Check echo'd command in the GPS packet
                for gg in filter(lambda p: p['exp_num'] == e_num, G_packets):
                    if gg['start_ind'] ==0:
                        cmd_gps = np.flip(gg['data'][0:3])
                        logger.debug(f'gps command: {cmd_gps}')
                        if (IB['prev_burst_command'] != cmd_gps).any():
                            logger.warning("GPS and status command echo mismatch")


                # Get burst configuration parameters:
                burst_config = decode_burst_command(IB['prev_burst_command'])
                burst_config['burst_pulses'] = IB['burst_pulses']

                logger.debug(f'burst configuration: {burst_config}')

                packets_to_process = list(filter(lambda p: p['exp_num'] == e_num, E_packets + B_packets + G_packets))
                processed = process_burst(packets_to_process, burst_config)


                processed['bbr_config'] = decode_uBBR_command(IB['prev_bbr_command'])
                processed['footer_timestamp'] = IB['header_timestamp']
                if IA:
                    processed['status'] = [IA, IB]
                    processed['header_timestamp'] = IA['header_timestamp']
                else:
                    processed['status'] = [IB]
                    processed['header_timestamp'] = min([x['header_timestamp'] for x in (E_packets + B_packets + G_packets)])
                processed['experiment_number'] = e_num

                completed_bursts.append(processed)
            except:
                logger.warning(f'Problem decoding burst {index}, exp_num {e_num}')
    logger.info(f'decoded {len(completed_bursts)} bursts')
    logger.info(f'{len(I_packets)} status packets remaining')
    return completed_bursts



def save_burst_to_file_tree(burst_data, out_root, filetypes):
    
    logger = logging.getLogger('save_burst_to_file_tree')
    for ftype in filetypes:
        if ftype not in ['xml','mat','pkl']:
            logger.warning(f'unsupported file type: {ftype}')
            continue
        
        for b in burst_data:
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

            logger.info(f'writing {outfile}')
            
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

    for ind, b in enumerate(bursts):
        try:
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
                try:
                    plot_burst_data([b], show_plots=False, filename=outfile, dpi=dpi, cal_file = cal_file)
                except:
                    logger.warning('Problem plotting burst data')
            if do_maps:
                try:
                    outfile = outfile.replace('VPM_burst_','VPM_map_')
                    plot_burst_map([b],show_plots=False, filename=outfile, dpi=dpi,
                                TLE_file=TLE_file, TX_file=TX_file)
                except:
                    logger.warning('Problem plotting burst map')
        except:
            logger.warning(f'Problem plotting burst {ind}')
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
    lookback_mins = int(config['burst_config']['lookback_time_minutes'])
    cal_file = config['burst_config']['calibration_file']
    dpi = int(config['burst_config']['dpi'])

    max_lookback_time = datetime.timedelta(minutes=lookback_mins)

    TLE_file = config['burst_config']['TLE_file'].strip()
    TX_file  = config['burst_config']['TX_file'].strip()
    access_log = config['logging']['access_log'].strip()


    last_timestamp = get_last_access_time(access_log,'process_burst_data')
    last_time = datetime.datetime.utcfromtimestamp(last_timestamp)
    logging.info(f'Last run time: {last_time} UTC')

    bursts = process_bursts_from_database(packet_db, date_added=last_time, max_lookback_time=max_lookback_time)

    # For debugging a smaller section:
    # t1 = datetime.datetime(2020,5,1,0,0,0, tzinfo=datetime.timezone.utc)
    # t2 = datetime.datetime(2020,5,6,0,0,0, tzinfo=datetime.timezone.utc)
    # bursts = process_bursts_from_database(packet_db, t1=t1, t2=t2,)

    # Save output files    
    save_burst_to_file_tree(bursts, out_root, file_types)

    if do_plots or do_maps:
        gen_burst_plots(bursts, out_root, do_plots=do_plots,
                 do_maps=do_maps, dpi=dpi, cal_file=cal_file,
                 TLE_file=TLE_file, TX_file=TX_file)

    # Success!
    logging.info(f'saving access time')
    log_access_time(access_log,'process_burst_data')

if __name__ == "__main__":
    main()