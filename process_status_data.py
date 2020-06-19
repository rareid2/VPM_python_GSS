import sys
import os
import datetime
import pickle
import gzip
import logging
import numpy as np
from configparser import ConfigParser

from file_handlers import load_packets_from_tree
from data_handlers import decode_status, unique_entries
from file_handlers import read_status_XML, write_status_XML
from db_handlers import get_packets_within_range, get_time_range_for_updated_packets
# from db_handlers import get_last_access_time, log_access_time
from log_handlers import get_last_access_time, log_access_time

def save_status_to_file_tree(stat_data, out_root):
    
    logger = logging.getLogger(__name__ + '.save_status_to_file_tree')

    dates = [datetime.datetime.fromtimestamp(x['header_timestamp'], tz=datetime.timezone.utc) for x in stat_data]
    days_to_do = np.unique([x.replace(hour=0, minute=0, second=0, microsecond=0) for x in dates])
    # print(days_to_do)

    for d in days_to_do:
        logger.info(f'doing {d}')
        t1 = d.timestamp()
        t2 = (d + datetime.timedelta(days=1)).timestamp()
        stat_filt = list(filter(lambda x: (x['header_timestamp'] >= t1) and (x['header_timestamp'] <= t2), stat_data))
        for file_format in ['xml']:
            logger.info(f'saving {len(stat_filt)} status entries')
            outpath = os.path.join(out_root,file_format,f'{d.year}', '{:02d}'.format(d.month),'{:02d}'.format(d.day))
            fname = f"VPM_status_messages_{d.strftime('%Y-%m-%d')}.{file_format}"
            # Check for previous file
            outfile = os.path.join(outpath, fname)
            logger.info(f'doing {outfile}')
            if not os.path.exists(outpath):
                logger.info(f'creating {outpath}')
                os.makedirs(outpath)
            if os.path.exists(outfile):
                logger.info('File exists! Overwriting')

                # -- Uncomment here to merge new entries with the old ones --
                #    (but the status task is so simple, so why bother)
                # logger.info('file exists! Loading previous entries')
                # stat_previous = read_status_XML(outfile)
                # logger.info(f'Joining {len(stat_previous)} entries with current {len(stat_filt)}')
                # stat_filt.extend(stat_previous)
                # len_pre_filt = len(stat_filt)
                # stat_filt = unique_entries(stat_filt)
                # logger.info(f'rejecting {len_pre_filt - len(stat_filt)} duplicate entries')

            logger.info(f'saving {len(stat_filt)} status entries')
            stat_filt = sorted(stat_filt, key=lambda x: x['header_timestamp'])
            write_status_XML(stat_filt, outfile)


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

    packet_db = config['db_locations']['packet_db_file']
    out_root = config['db_locations']['status_tree_root']
    access_log = config['logging']['access_log']

 
    last_timestamp = get_last_access_time(access_log,'process_status_data')
    last_time = datetime.datetime.utcfromtimestamp(last_timestamp)
    logging.info(f'Last run time: {last_time} UTC')

    tsmin, tsmax = get_time_range_for_updated_packets(packet_db, last_timestamp)

    if (not tsmin) or (not tsmax):
        logging.info('No new data to process')
    else:    
        logging.info(f'Header timestamps range from {datetime.datetime.utcfromtimestamp(tsmin)} to {datetime.datetime.utcfromtimestamp(tsmax)}')
        # Add in some extra margin, in case the new minimum is in the middle of a burst
        tmin = datetime.datetime.utcfromtimestamp(tsmin) - datetime.timedelta(hours=2)
        tmax = datetime.datetime.utcfromtimestamp(tsmax) + datetime.timedelta(hours=2)
        logging.info(f'Loading packets with header timestamps {tmin} to {tmax}')

        stats = []
        # ---------------- Load packets --------------------
        # packets = load_packets_from_tree(in_root)
        packets = get_packets_within_range(packet_db, dtype='I', t1=tmin, t2=tmax)


        logging.info(f'loaded {len(packets)} packets')
        if packets:
            stats.extend(decode_status(packets))
            logging.info(f'Decoded {len(stats)} status messages')

        if stats:
            save_status_to_file_tree(stats, out_root)
  
    log_access_time(access_log,'process_status_data')
            
if __name__=="__main__":
    main()