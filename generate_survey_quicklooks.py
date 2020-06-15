import sys
import os
import datetime
import pickle
import gzip
from scipy.io import savemat
import matplotlib.pyplot as plt
import numpy as np
from configparser import ConfigParser


from file_handlers import read_status_XML, read_burst_XML, read_survey_XML, write_survey_XML
from data_handlers import decode_packets_TLM, decode_packets_CSV, decode_survey_data
# from db_handlers import log_access_time, get_last_access_time
from cli_plots import plot_survey_data_and_metadata
from log_handlers import get_last_access_time, log_access_time

import logging

# --------------- Latex Plot Beautification --------------------------
fig_width = 12
fig_height = 8
fig_size =  [fig_width+1,fig_height+1]
params = {'backend': 'ps',
          'axes.labelsize': 8,
          'font.size': 10,
          'legend.fontsize': 8,
          'xtick.labelsize': 8,
          'ytick.labelsize': 8,
          'text.usetex': False,
          'figure.figsize': fig_size}
plt.rcParams.update(params)
# --------------- Latex Plot Beautification --------------------------

def get_timestamp(x):
    try:
        ts = x['GPS'][0]['timestamp']
    except:
        print("entry is missing GPS data")
        ts = x['header_timestamp']
    return ts


def generate_survey_quicklooks(in_root, out_root, 
        start_date=None, stop_date=None, plot_length=6, last_run_time=None,
        line_plots = ['Lshell','altitude','lat','lon','used_sats','solution_status','daylight']):

    logger = logging.getLogger('generate_survey_quicklooks')


    if not last_run_time:
        last_run_time=datetime.datetime.utcfromtimestamp(0)
    if not start_date:
        start_date = datetime.datetime(1980,1,1,0,0,0)
    if not stop_date:
        stop_date = datetime.datetime.now()

    # edges for plot times
    hour_segs = np.arange(0,25,plot_length)

    for root, dirs, files in os.walk(in_root):
        for fname in files:
            if fname.startswith('VPM_survey_data_') and fname.endswith('.xml'):

                filetime = datetime.datetime.utcfromtimestamp(os.path.getmtime(os.path.join(root, fname)))
                if filetime < last_run_time:
                    logger.info(f'skipping {fname} (no changes since {last_run_time})')
                else:
                    day = datetime.datetime.strptime(fname, 'VPM_survey_data_%Y-%m-%d.xml')
                    if (day >= start_date) and (day <= stop_date):

                        filename = os.path.join(root, fname)
                        print(f'Loading {filename}')
                        S_data = read_survey_XML(filename)

                        for h1,h2 in zip(hour_segs[:-1], hour_segs[1:]):
                                d1 = day + datetime.timedelta(hours=int(h1))
                                d2 = day + datetime.timedelta(hours=int(h2))
                                t1 = d1.replace(tzinfo = datetime.timezone.utc).timestamp()
                                t2 = d2.replace(tzinfo = datetime.timezone.utc).timestamp()
                                S_filt = list(filter(lambda x: (get_timestamp(x) >= t1) and (get_timestamp(x) < t2), S_data))
                                
                                outdir = os.path.join(out_root,f'{day.year}','{:02d}'.format(day.month))

                                if S_filt:            
                                    fig = plot_survey_data_and_metadata(S_filt, filename='survey_data_with_metadata.pdf',t1=d1, t2=d2,
                                                  line_plots = line_plots,
                                                  show_plots=False, lshell_file='resources/Lshell_dict.pkl')
                                    
                                    fig.suptitle(f"VPM Survey Data: {day.strftime('%D')}\n" +\
                                            f"{d1.strftime('%H:%M:%S')} -- {d2.strftime('%H:%M:%S')} UT")
                                    
                                    if not os.path.exists(outdir):
                                        os.makedirs(outdir)
                                    
                                    outfile = os.path.join(outdir,
                                                f"VPM_survey_data_{d1.strftime('%Y-%m-%d_%H%M--')}{d2.strftime('%H%M')}.png")

                                    fig.savefig(outfile, dpi=120)

                                    plt.close(fig)



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

    in_root = os.path.join(config['db_locations']['survey_tree_root'],'xml')
    out_root = os.path.join(config['db_locations']['survey_tree_root'],'figures')
    line_plots = [x.strip() for x in config['survey_config']['line_plots'].split(',')]
    plot_length = int(config['survey_config']['plot_length'])
    packet_db_file = config['db_locations']['packet_db_file']
    access_log = config['logging']['access_log']

    last_timestamp = get_last_access_time(access_log, 'generate_survey_quicklooks')
    last_run_time = datetime.datetime.utcfromtimestamp(last_timestamp)

    logging.info(f'Last ran at {last_run_time}')
    generate_survey_quicklooks(in_root, out_root, line_plots = line_plots, 
        plot_length=plot_length, last_run_time=last_run_time)

    # Success!
    log_access_time(access_log,"generate_survey_quicklooks")

if __name__ == "__main__":
    main()