import sys
import os

import gzip
import pickle
import numpy as np
import datetime
import matplotlib.pyplot as plt
from configparser import ConfigParser

from data_handlers import decode_packets_TLM, decode_packets_CSV
from data_handlers import decode_survey_data
from data_handlers import unique_entries

from db_handlers import write_to_db, connect_packet_db, get_files_in_db
from log_handlers import get_last_access_time, log_access_time

import logging


def load_from_telemetry(filepath, files_to_skip = [], do_TLM=True, do_CSV=True):
    ''' Walk through a file tree, and process any TLM and CSV files we can find '''
    # -------- Process all TLM and CSV files we can find -----------

    logger = logging.getLogger('load_from_telemetry')
    packets = []

    for root, dirs, files in os.walk(filepath):

        for fname in files:
            if fname in files_to_skip:
                logger.debug(f'File {fname} already in database; skipping')
            else:
                try:
                    if do_TLM and fname.endswith('.tlm'):
                        logger.info(f'loading TLM from {root} {fname}')
                        # Load packets from each TLM file, tag with the source filename, and decode
                        packets.extend(decode_packets_TLM(root, fname))

                    if do_CSV and fname.endswith('.csv'):
                        logger.info(f'loading CSV from {root} {fname}')
                        packets.extend(decode_packets_CSV(root, fname))
                except:
                    logger.warning(f'Problem loading {fname}')

    return packets


def save_packets_to_file_tree(packets, filepath, out_root):
    ''' Save a list of decoded packets to a sorted filetree.
        if a previous file already exists, load it, remove duplicates, sort, and rewrite.
    '''

    logger = logging.getLogger('save_packets_to_file_tree')
    dates = [datetime.datetime.fromtimestamp(x['header_timestamp'], tz=datetime.timezone.utc) for x in packets]
    days_to_do = np.unique([x.replace(hour=0, minute=0, second=0, microsecond=0) for x in dates])

    print(days_to_do)

    for d in days_to_do:
        logger.info(f'doing {d}')
        t1 = d.timestamp()
        t2 = (d + datetime.timedelta(days=1)).timestamp()
        P_filt = list(filter(lambda x: (x['header_timestamp'] >= t1) and (x['header_timestamp'] < t2), packets))
        
        outpath = os.path.join(out_root,'Packets',f'{d.year}', '{:02d}'.format(d.month),'{:02d}'.format(d.day))
        fname = f"VPM_packets_{d.strftime('%Y-%m-%d')}.pklz"
        
        logger.info(f'\tDoing {len(P_filt)} packets')

        if P_filt:
            outfile = os.path.join(outpath, fname)
            if not os.path.exists(outpath):
                logger.info(f'making directory {outpath}')
                os.makedirs(outpath)
                
            # Check for previous file
            if os.path.exists(outfile):
                logger.info('\tfile exists! Loading previous entries')
            
                try:
                    with gzip.open(outfile,'rb') as file:
                        P_previous = pickle.load(file)
                        logger.info(f'\t\tmerging {len(P_previous)} previous entries with {len(P_filt)} new entries')
                        P_filt.extend(P_previous)
                        len_pre_filt = len(P_filt)
                        P_filt = unique_entries(P_filt)
                        logger.info(f'\t\trejecting {len_pre_filt - len(P_filt)} duplicate entries')
                except:
                    logger.exception('Problem reading previous file')
            # Sort the packets by arrival time
            P_filt = sorted(P_filt, key=lambda x: x['header_timestamp'])
            
            # Save it:
            with gzip.open(outfile,'wb') as file:
                pickle.dump(P_filt, file)


def process_packets():

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
    
    output_type = 'db'
    # output_type = 'files'
    # You need this setting if you're using a file tree for the raw packets
    # (but the database is cooler)
    # out_root = config['db_locations']['packet_tree_root']

    in_roots = config['db_locations']['telemetry_watch_directory'].split(',')
    db_name = config['db_locations']['packet_db_file']
    access_log = config['logging']['access_log']

    do_TLM = True
    do_CSV = True

    logging.info(f'input paths: {in_roots}')
    

    # Find any files to exclude from this run
    # (We could also do this by tracking the file modification date)
    if 'db' in output_type:
        logging.info(f'output database: {db_name}')
        files_to_skip = get_files_in_db(db_name, 'packets')
    else:
        logging.info(f'output path: {out_root}')
        files_to_skip = []

    # logging.info(f'Files to skip: {files_to_skip}')

    for in_root in in_roots:
        logging.info(f'doing {in_root}:')

        for root, dirs, files in os.walk(in_root):

                for fname in files:
                    if fname in files_to_skip:
                        logging.debug(f'File {fname} already in database; skipping')
                    else:

                        packets = []
                        try:
                            if do_TLM and fname.endswith('.tlm'):
                                logging.info(f'loading TLM from {root} {fname}')
                                # Load packets from each TLM file, tag with the source filename, and decode
                                packets = decode_packets_TLM(root, fname)

                            if do_CSV and fname.endswith('.csv'):
                                logging.info(f'loading CSV from {root} {fname}')
                                packets = decode_packets_CSV(root, fname)

                            if packets:
                                if 'files' in output_type:
                                    save_packets_to_file_tree(packets, out_root)
                                if 'db' in output_type:
                                    conn = connect_packet_db(db_name)
                                    line_id = write_to_db(conn, packets, db_field='packets')
                                    logging.info(f'wrote to db: line ID = {line_id}')
                                    conn.commit()
                                    conn.close()

                        except:
                            logging.warning(f'Problem loading {fname}')




    if 'db' in output_type:
        log_access_time(access_log, 'process_packets')


if __name__ == "__main__":
    process_packets()