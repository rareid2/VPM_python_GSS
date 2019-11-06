import numpy as np
import pickle
import scipy.stats
from decode_burst_command import decode_burst_command
from decode_GPS_data import decode_GPS_data
from decode_status import decode_status
import matplotlib.pyplot as plt
import datetime
import itertools


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

    out_list = []

    # Select burst packets
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    I_packets     = sorted(I_packets, key = lambda p: p['header_timestamp'])
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    stats = decode_status(I_packets)
    # Get all unique experiment numbers for this set of packets 
    # (chances are real good that we'll only have 1 or 2 unique numbers)
    avail_exp_nums = np.unique([x['exp_num'] for x in E_packets + B_packets])
    print("available burst experiment numbers:",avail_exp_nums)
    # e_num = scipy.stats.mode(avail_exp_nums[0])[0][0] # Pick the one we have the most of

    completed_bursts = []

    outs = dict() # The output container

    # Do we have any corresponding status packets?
    # These are tagged with p['data'][3] == 'B', and are requested at 
    # either end of a burst. 
    
    
    # Grab the burst command from the first status packets

    # if I_packets:
    #     print("Using command from status packet")
    #     cmd = np.flip(I_packets[0]['data'][12:15])
    #     burst_config = decode_burst_command(cmd)

    #     # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
    #     system_config = np.flip(I_packets[0]['data'][20:24])
    #     system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
    #     burst_config['burst_pulses'] = int(system_config[16:24],base=2)

    # else:
    #     print("Using manually-assigned burst command")
    #     burst_config = decode_burst_command([96,0,0])
    #     burst_config['burst_pulses'] = 1;

        # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
    system_config = np.flip(I_packets[0]['data'][20:24])
    system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
    pulses = int(system_config[16:24],base=2)
    print('pulses:', pulses)

    for e_num in avail_exp_nums:
        print("processing experiment number", e_num)
        filt_inds = [p['exp_num']==e_num for p in burst_packets]
        current_packets = list(itertools.compress(burst_packets, filt_inds))

        current_packets = list(filter(lambda p: p['exp_num']==e_num, burst_packets))
        cur_G_packets   = list(filter(lambda p: p['dtype']=='G', current_packets))

        # Burst command is echo'ed at the top of each GPS packet:
        for g in cur_G_packets:
            cmd = np.flip(g['data'][0:3])
            burst_config = decode_burst_command(cmd)
            burst_config['burst_pulses'] = pulses
            print(cmd)

        # Remove processed packets from data_dict
        # burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))


        processed = process_burst(current_packets, burst_config)
        completed_bursts.append(processed)
        burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
        print("remaining packets:", len(burst_packets))
    unused_packets = burst_packets
    return completed_bursts, unused_packets


def decode_burst_data(packets):
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

    # -------- arrival time debugging plot -------
    fig, ax = plt.subplots(1,1)
    taxis = np.arange(len(burst_packets))    
    tstamps = np.array([p['header_timestamp'] for p in burst_packets])
    dtypes  = np.array([p['dtype'] for p in burst_packets])
    ax.plot(taxis[dtypes=='E'], tstamps[dtypes=='E'],'b.', label='E')
    ax.plot(taxis[dtypes=='B'], tstamps[dtypes=='B'],'r.', label='B')
    ax.plot(taxis[dtypes=='G'], tstamps[dtypes=='G'],'g.', label='G')
    ax.hlines([p['header_timestamp'] for p in I_packets], 0, len(burst_packets))
    ax.legend()
    ax.set_xlabel('arrival index')
    ax.set_ylabel('timestamp')
    plt.show()
    print(np.unique([p['exp_num'] for p in burst_packets]))
    # --------------------------------------------

    # Sort packets into data_dict to combine with previous data
    # for p in (E_packets + B_packets + G_packets):
    # for p in burst_packets:
    #     data_dict[p['exp_num']].append(p)

    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])
    # You need to put this in the dictionary some time... 
    # data_dict['I'].extend(I_packets)

    completed_bursts = []

    status_times = np.array(sorted([IP['header_timestamp'] for IP in I_packets]))


    # for e_num, cur_packets in data_dict.items():
        # processed = process_burst(cur_packets)
    # fig,ax = plt.subplots(1,1)
    # ax.plot([p['header_timestamp'] for p in burst_packets],'.')
    # ax.hlines([p['header_timestamp'] for p in I_packets], 0, len(burst_packets))
    # plt.show()
    # We should get a status message at the beginning and end of each burst.
    # Add 1 second padding on either side for good measure.
    # # for ta,tb in zip(status_times[0:-1] - 1, status_times[1:] + 1, ):
    print(f'I_packets has length {len(I_packets)} pre-sift')
    for IA, IB in zip(I_packets[0:-1], I_packets[1:]):
        ta = IA['header_timestamp'] - 1.5
        tb = IB['header_timestamp'] + 1.5
        print(ta, tb)
        
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
            print(f"packets in time range: {len(packets_in_time_range)}; packets with exp_num {e_num}: {len(packets_with_matching_e_num)}")
            # packets_in_time_range = list(filter(lambda p: p['header_timestamp'] >= ta and p['header_timestamp'] <= tb, data_dict[e_num]))           
            # packets_outside_range = list(filter(lambda p: p['header_timestamp']  < ta or  p['header_timestamp']  > tb, data_dict[e_num]))           


            if len(packets_in_time_range) > 100:
                print(f'------ exp num {e_num} ------')
                print("status packet times:",datetime.datetime.utcfromtimestamp(ta),datetime.datetime.utcfromtimestamp(tb))

                # Ok! Now we have a list of packets, all with a common experiment number, 
                # in between two status packets, each with have the same burst command.
                # Ideally, this should be a complete set of burst data. Let's try processing it!
                
                for gg in filter(lambda packet: packet['dtype'] == 'G', packets_in_time_range):
                    if gg['start_ind'] ==0:
                        cmd_gps = np.flip(gg['data'][0:3])
                        if (IA_cmd != cmd_gps).any():
                            print("GPS and status command echo mismatch")

                # Get burst configuration parameters:
                cmd = np.flip(IA['data'][12:15])
                burst_config = decode_burst_command(cmd)
                

                # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
                system_config = np.flip(IA['data'][20:24])
                system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
                burst_config['burst_pulses'] = int(system_config[16:24],base=2)

                print(burst_config)

                processed = process_burst(packets_in_time_range, burst_config)
                processed['I'] = [IA, IB]
                processed['header_timestamp'] = ta
                completed_bursts.append(processed)

                # Remove processed packets from data_dict
                burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
                I_packets.remove(IA)
                I_packets.remove(IB)

    # print(f'I_packets has length {len(I_packets)}')
    # tmp = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    # print(f'original packet list still has {len(tmp)} packets')
    print(f'{len(burst_packets)} unused packets')
    unused_packets = burst_packets + I_packets
    return completed_bursts, unused_packets

def process_burst(packets, burst_config):
    ''' Reassemble burst data, according to info in burst_config.
        This assumes the set of packets is complete, and belongs to the
        same burst.
    '''

    # Sort the packets by data stream:
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))

    if burst_config['TD_FD_SELECT']==1:
        # Initialize for time domain
        n_samples = 2*burst_config['SAMPLES_ON']*burst_config['burst_pulses'] # how many 8-bit values should we get?
    elif burst_config['TD_FD_SELECT']==0:
        # Initialize for frequency domain
        seg_length = 32 #1024/2/16 # number of FFTs within each "bin"
        print("seg length:", seg_length)
        n_samples = int(2*(burst_config['FFTS_ON'])*2*seg_length*burst_config['BINS'].count('1'))


    # # Loop through all packets to get the maximum data index:        
    max_E_ind = max([p['start_ind'] + p['bytecount'] for p in E_packets])
    max_B_ind = max([p['start_ind'] + p['bytecount'] for p in B_packets])
    max_G_ind = max([p['start_ind'] + p['bytecount'] for p in G_packets])

    E_data = np.zeros(max_E_ind)*np.nan
    B_data = np.zeros(max_B_ind)*np.nan
    G_data = np.zeros(max_G_ind)*np.nan

    print(f'Max E ind: {max_E_ind}  Max B ind: {max_B_ind}, Max G ind: {max_G_ind}')
    print("reassembling E")
    for p in E_packets:
        E_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    print("reassembling B")
    for p in B_packets:
        B_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    print("reassembling GPS")
    for p in G_packets:
        G_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    with open("raw_as_hell.pkl","wb") as f:
        pickle.dump(E_data, f)
    # Juggle the 8-bit values around
    if burst_config['TD_FD_SELECT']==1:
        print("Selected time domain")
        E = TD_reassemble(E_data)
        B = TD_reassemble(B_data)


    if burst_config['TD_FD_SELECT']==0:
        print("seleced frequency domain")
        E = FD_reassemble(E_data)
        B = FD_reassemble(B_data)

    print(f'Reassembled E has length {len(E)}, with {np.sum(np.isnan(E))} nans. Raw E missing {np.sum(np.isnan(E_data))} values.')
    print(f'Reassembled B has length {len(B)}, with {np.sum(np.isnan(B))} nans. Raw B missing {np.sum(np.isnan(B_data))} values.')
    print(f'expected {int(n_samples/2)} samples')

    # Decode any GPS data we might have
    # print(' '.join([hex(int(j)) for j in G_data[0:24]]))
    G = decode_GPS_data(G_data)
    outs = dict()
    outs['E'] = E
    outs['B'] = B
    outs['G'] = G
    outs['config'] = burst_config

    return outs

if __name__ == '__main__':

    with open('packets.pkl','rb') as f:
        packets = pickle.load(f)

    # stats = decode_status(packets)
    # for s in stats:
    #     print(s)
    burst, unused = decode_burst_data(packets)
    outs = dict()
    outs['burst'] = burst
    with open('decoded_data.pkl','wb') as f:
        pickle.dump(outs,f)

    # with open('burst_raw.pkl','wb') as f:
    #     pickle.dump(outs, f)