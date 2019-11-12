import numpy as np
import pickle
import scipy.stats
from decode_burst_command import decode_burst_command
from decode_GPS_data import decode_GPS_data
from decode_status import decode_status
import matplotlib.pyplot as plt
import datetime
import itertools
import os
from plot_burst_data import plot_burst_data
from packet_inspector import packet_inspector
import logging

def remove_trailing_nans(arr1d):
    ''' Trims off the trailing NaNs of a vector.'''
    notnans = np.flatnonzero(~np.isnan(arr1d))
    if notnans.size:
        # Trim leading and trailing:
#         trimmed = arr1d[notnans[0]: notnans[-1]+1]  # slice from first not-nan to the last one
        # Trim trailing only
        trimmed = arr1d[0:notnans[-1]+1]  # slice from first not-nan to the last one
    else:
        trimmed = np.zeros(0)
    # print(f"arr has {np.sum(np.isnan(arr1d))} nans")
    # print(f"Trim has {np.sum(np.isnan(trimmed))} nans")
        
    return trimmed

def TD_reassemble(vec):
    ''' Rearranges a byte string into 16-bit values (packed as a double),
     following time-domain interleaving'''
    
    re = vec[:len(vec) - (len(vec)%4)].astype('uint8')
    re = np.reshape(re, [int(len(re)/4),4])
    re = np.stack([(re[:,0] + 256*re[:,1]).astype('int16'), (re[:,2] + 256*re[:,3]).astype('int16')],axis=1)
    re = re.ravel().astype('float')

    # Mark off any nans in the output vector
    out_nan_inds = np.unique(np.floor(np.where(np.isnan(vec))[0]/2).astype('int'))
    re[out_nan_inds] = np.nan

    # Returns floats, even though our data is 16-bit ints... but this keeps the 'nan' flags present.
    return re


def FD_reassemble(vec):
    ''' Rearranges a byte string into 16-bit values (packed as a complex double),
    following time-domain interleaving.
    Untested as of 10/11/2019, but follows the Matlab code! I need some FD data to try it with.

    Added nan mask 10/31/2019, also untested
    '''
    re = vec[:len(vec) - (len(vec)%4)].astype('uint8')
    re = np.reshape(re, [int(len(re)/4),4])
    re = np.stack([(re[:,0] + 256*re[:,1]).astype('int16'), (re[:,2] + 256*re[:,3]).astype('int16')],axis=1)

    re = re[:,0].astype('float') + 1j*re[:,1].astype('float')

    # Mark off any nans in the output vector.
    out_nan_inds = np.unique(np.floor(np.where(np.isnan(vec))[0]/4).astype('int'))
    re[out_nan_inds] = np.nan

    return re


def decode_burst_data_by_experiment_number(packets, burst_cmd = None):
    ''' Decode bursts by grouping packets by experiment number.
        The burst command is echoed in each GPS packet; the number of repeats
        is decoded by counting GPS packets.

        This method is the way things should work ideally -- however, it will
        fail on bursts without GPS data, either from dropped packets or the GPS
        card being turned off, and may cause problems if the payload has been
        reset between two adjacent bursts, resulting in two bursts with experiment
        number 0.
    '''
    logger = logging.getLogger(__name__)

    out_list = []

    # Select burst packets
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    
    # Get all unique experiment numbers for this set of packets 
    # (chances are real good that we'll only have 1 or 2 unique numbers)
    avail_exp_nums = np.unique([x['exp_num'] for x in E_packets + B_packets])
    logger.info(f"available burst experiment numbers: {avail_exp_nums}")

    completed_bursts = []

    outs = dict() # The output container

    for e_num in avail_exp_nums:
        logger.info(f"processing experiment number {e_num}")
        filt_inds = [p['exp_num']==e_num for p in burst_packets]
        current_packets = list(itertools.compress(burst_packets, filt_inds))
        current_packets = list(filter(lambda p: p['exp_num']==e_num, burst_packets))
        cur_G_packets   = list(filter(lambda p: p['dtype']=='G', current_packets))
        header_timestamps = sorted([p['header_timestamp'] for p in current_packets])
        
        # packet_inspector(current_packets)
        # Burst command is echo'ed at the top of each GPS packet:
        gps_echoed_cmds = []
        for g in cur_G_packets:
            if g['start_ind'] == 0:
                cmd = np.flip(g['data'][0:3])
                gps_echoed_cmds.append(cmd)

        if gps_echoed_cmds:
            # Check that they're all the same, if we have more entries...
            cmd = gps_echoed_cmds[0]
            burst_config = decode_burst_command(cmd)
        else:
            logger.warning("no GPS packets found; cannot determine burst command")                
            continue
        
        processed = process_burst(current_packets, burst_config)
        processed['header_timestamp'] = header_timestamps[0]


        completed_bursts.append(processed)
        burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
        logger.info(f"{len(burst_packets)} packets remaining")
    unused_packets = burst_packets
    return completed_bursts, unused_packets



def decode_burst_data_in_range(packets, ta, tb, burst_cmd = None, burst_pulses = 1):
    ''' decode burst data between a given time interval, with a given command.
        Use this in the event that we want to decode an incomplete burst.
    '''
    logger = logging.getLogger(__name__)

    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    I_packets     = sorted(I_packets, key = lambda p: p['header_timestamp'])
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    stats = decode_status(I_packets)

    packet_inspector(packets + I_packets)

    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])

    completed_bursts = []

    for e_num in avail_exp_nums:
        
        filt_inds = [p['header_timestamp'] >= ta and p['header_timestamp'] <= tb for p in burst_packets]
        packets_in_time_range = list(itertools.compress(burst_packets, filt_inds))

        packets_with_matching_e_num = list(filter(lambda p: p['exp_num']==e_num, burst_packets))
        logger.info(f"packets in time range: {len(packets_in_time_range)}; packets with exp_num {e_num}: {len(packets_with_matching_e_num)}")

        if len(packets_in_time_range) > 100:
            logger.info(f'------ exp num {e_num} ------')
            logger.info(f"status packet times: {datetime.datetime.utcfromtimestamp(ta),datetime.datetime.utcfromtimestamp(tb)}")

            # # Ok! Now we have a list of packets, all with a common experiment number, 
            # # in between two status packets, each with have the same burst command.
            # # Ideally, this should be a complete set of burst data. Let's try processing it!
            
            for gg in filter(lambda packet: packet['dtype'] == 'G', packets_in_time_range):
                if gg['start_ind'] ==0:
                    cmd_gps = np.flip(gg['data'][0:3])
                    logger.info(cmd_gps)
                    
            # Get burst configuration parameters:
            burst_config = decode_burst_command(burst_cmd)
            burst_config['burst_pulses'] = burst_pulses

            logger.info(burst_config)

            processed = process_burst(packets_in_time_range, burst_config)
            # processed['I'] = [IA, IB]
            processed['burst_config'] = burst_config
            processed['ta'] = ta
            processed['tb'] = tb
            # processed['header_timestamp'] = ta
            completed_bursts.append(processed)

    return completed_bursts

def decode_burst_data_between_status_packets(packets):
    ''' Decode burst data by sorting packets by arrival time, and binning bursts
        between two status packets. 
    '''

    logger = logging.getLogger(__name__)

    # Select burst packets
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    I_packets     = sorted(I_packets, key = lambda p: p['header_timestamp'])
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    stats = decode_status(I_packets)
    # for s in stats:
    #     print(s)
    packet_inspector(packets)

    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])

    completed_bursts = []

    status_times = np.array(sorted([IP['header_timestamp'] for IP in I_packets]))

    # We should have a status message at the beginning and end of each burst.
    # Add 1 second padding on either side for good measure.
    # # for ta,tb in zip(status_times[0:-1] - 1, status_times[1:] + 1, ):
    logger.info(f'I_packets has length {len(I_packets)} pre-sift')
    for IA, IB in zip(I_packets[0:-1], I_packets[1:]):
        ta = IA['header_timestamp'] - 1.5
        tb = IB['header_timestamp'] + 1.5
        logger.info(f"{ta}, {tb}")
        
    #     # Let's confirm that the burst command is the same within each status packet:        
        IA_cmd = np.flip(IA['data'][12:15])
        IB_cmd = np.flip(IB['data'][12:15])

        # Skip any pairs with different burst commands (this might be questionable...)
        if any(IA_cmd != IB_cmd):
            continue

        # for e_num in data_dict.keys():
        for e_num in avail_exp_nums:

            filt_inds = [p['header_timestamp'] >= ta and p['header_timestamp'] <= tb for p in burst_packets]
            packets_in_time_range = list(itertools.compress(burst_packets, filt_inds))


            packets_with_matching_e_num = list(filter(lambda p: p['exp_num']==e_num, burst_packets))
            logger.info(f"packets in time range: {len(packets_in_time_range)}; packets with exp_num {e_num}: {len(packets_with_matching_e_num)}")
            # packets_in_time_range = list(filter(lambda p: p['header_timestamp'] >= ta and p['header_timestamp'] <= tb, data_dict[e_num]))           
            # packets_outside_range = list(filter(lambda p: p['header_timestamp']  < ta or  p['header_timestamp']  > tb, data_dict[e_num]))           


            if len(packets_in_time_range) > 100:
                logger.info(f'------ exp num {e_num} ------')
                logger.info(f"status packet times: {datetime.datetime.utcfromtimestamp(ta),datetime.datetime.utcfromtimestamp(tb)}")

                # Ok! Now we have a list of packets, all with a common experiment number, 
                # in between two status packets, each with have the same burst command.
                # Ideally, this should be a complete set of burst data. Let's try processing it!
                
                for gg in filter(lambda packet: packet['dtype'] == 'G', packets_in_time_range):
                    if gg['start_ind'] ==0:
                        cmd_gps = np.flip(gg['data'][0:3])
                        logger.debug(cmd_gps)
                        if (IA_cmd != cmd_gps).any():
                            logger.warning("GPS and status command echo mismatch")

                # Get burst configuration parameters:
                cmd = np.flip(IA['data'][12:15])
                burst_config = decode_burst_command(cmd)
                

                # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
                system_config = np.flip(IA['data'][20:24])
                system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
                burst_config['burst_pulses'] = int(system_config[16:24],base=2)

                logger.info(burst_config)

                processed = process_burst(packets_in_time_range, burst_config)
                processed['I'] = [IA, IB]
                processed['header_timestamp'] = ta
                completed_bursts.append(processed)

                # Remove processed packets from data_dict
                burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
                I_packets.remove(IA)
                I_packets.remove(IB)

    logger.info(f'{len(burst_packets)} unused packets')
    unused_packets = burst_packets + I_packets
    return completed_bursts, unused_packets

def process_burst(packets, burst_config):
    ''' Reassemble burst data, according to info in burst_config.
        This assumes the set of packets is complete, and belongs to the
        same burst.

        This is the internal helper function called by the other "Decode burst" methods.
    '''

    logger = logging.getLogger(__name__)

    # Sort the packets by data stream:
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))



    # Loop through all packets to get the maximum data index:    
    if E_packets:
        max_E_ind = max([p['start_ind'] + p['bytecount'] for p in E_packets])
    else: max_E_ind = 0
    if B_packets:
        max_B_ind = max([p['start_ind'] + p['bytecount'] for p in B_packets])
    else: max_B_ind = 0
    if G_packets:
        max_G_ind = max([p['start_ind'] + p['bytecount'] for p in G_packets])
    else: max_G_ind = 0

    E_data = np.zeros(max_E_ind)*np.nan
    B_data = np.zeros(max_B_ind)*np.nan
    G_data = np.zeros(max_G_ind)*np.nan

    logger.debug(f'Max E ind: {max_E_ind}  Max B ind: {max_B_ind}, Max G ind: {max_G_ind}')
    logger.info("reassembling E")
    for p in E_packets:
        E_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    logger.info("reassembling B")
    for p in B_packets:
        B_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    logger.info("reassembling GPS")
    for p in G_packets:
        G_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']


    # Decode any GPS data we might have
    G = decode_GPS_data(G_data)

    # One GPS entry per pulse
    if (G):
        burst_config['burst_pulses'] = len(G)

    # ------- Calculate n_samples -------
    # This isn't really used here anymore! All we need to know in here is time domain or frequency domain...
    if burst_config['TD_FD_SELECT']==1:
        SAMPLES_TO_IGNORE = 105;
        # Initialize for time domain
        n_samples = 2*burst_config['SAMPLES_ON']*burst_config['burst_pulses'] # how many 8-bit values should we get?
        if burst_config['DECIMATE_ON']==1:
            # (Not sure about this)
            n_samples = n_samples/burst_config['DECIMATION_FACTOR']
            n_samples -= np.floor(SAMPLES_TO_IGNORE/burst_config['DECIMATION_FACTOR']) + burst_config['DECIMATION_FACTOR'] - 1
            
    elif burst_config['TD_FD_SELECT']==0:
        # Initialize for frequency domain
        seg_length = 32 # number of FFTs within each bin
        logger.info(f"seg length: {seg_length}")
        n_samples = int(2*(burst_config['FFTS_ON'])*2*seg_length*burst_config['BINS'].count('1'))

    # Juggle the 8-bit values around
    if burst_config['TD_FD_SELECT']==1:
        logger.info("Selected time domain")
        E = TD_reassemble(E_data)
        B = TD_reassemble(B_data)

    if burst_config['TD_FD_SELECT']==0:
        logger.info("seleced frequency domain")
        E = FD_reassemble(E_data)
        B = FD_reassemble(B_data)

    logger.debug(f'Reassembled E has length {len(E)}, with {np.sum(np.isnan(E))} nans. Raw E missing {np.sum(np.isnan(E_data))} values.')
    logger.debug(f'Reassembled B has length {len(B)}, with {np.sum(np.isnan(B))} nans. Raw B missing {np.sum(np.isnan(B_data))} values.')
    logger.debug(f'expected {int(n_samples/2)} samples')


    outs = dict()
    outs['E'] = E
    outs['B'] = B
    outs['G'] = G
    outs['config'] = burst_config

    return outs

if __name__ == '__main__':

    with open('output/packets.pkl','rb') as f:
        packets = pickle.load(f)

    # stats = decode_status(packets)
    # for s in stats:
    #     print(s)
    print(np.shape(packets))
    # bursts, unused = decode_burst_data(packets)
    bursts, unused = decode_burst_data_by_experiment_number(packets)

    # Manually process data between times ta and tb, with a given burst commmand.
    # Does not remove used packets, doesn't return unused packets...
    # ta = datetime.datetime(2019,1,1,0,0,0, tzinfo=datetime.timezone.utc).timestamp()
    # tb = datetime.datetime(2019,1,1,0,0,1, tzinfo=datetime.timezone.utc).timestamp()
    # bursts = decode_burst_data_in_range(packets, ta, tb, burst_cmd=np.array([96, 160, 0]).astype('int'), burst_pulses = 1)


    # bursts, unused = decode_burst_data_by_experiment_number(packets, np.array([96, 160, 0]).astype('int'))
    outs = dict()
    outs['burst'] = bursts
    with open('manually_processed_burst.pkl','wb') as f:
        pickle.dump(outs, f)


    plot_burst_data(outs['burst'])

    # burst, unused = decode_burst_data(packets)
    # outs = dict()
    # outs['burst'] = burst
    # with open('decoded_data.pkl','wb') as f:
    #     pickle.dump(outs,f)

    # # with open('burst_raw.pkl','wb') as f:
    # #     pickle.dump(outs, f)