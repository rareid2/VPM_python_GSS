import numpy as np
import pickle
import scipy.stats
from decode_burst_command import decode_burst_command
from decode_GPS_data import decode_GPS_data
from decode_status import decode_status
import matplotlib.pyplot as plt
import datetime


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


# def decode_burst_data(packets, burst_cmd = None):

#     out_list = []

#     E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
#     B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
#     G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))

#     # Get all unique experiment numbers for this set of packets 
#     # (chances are real good that we'll only have 1 or 2 unique numbers)
#     avail_exp_nums = np.unique([x['exp_num'] for x in E_packets + B_packets])
#     print("available burst experiment numbers:",avail_exp_nums)
#     # e_num = scipy.stats.mode(avail_exp_nums[0])[0][0] # Pick the one we have the most of
#     for e_num in avail_exp_nums:
        
#         outs = dict() # The output container

#         # Do we have any corresponding status packets?
#         # These are tagged with p['data'][3] == 'B', and are requested at 
#         # either end of a burst. 
#         I_packets = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
        
#         # Grab the burst command from the first status packet.
#         if I_packets:
#             print("Using echoed burst command")
#             cmd = np.flip(I_packets[0]['data'][12:15])
#             burst_config = decode_burst_command(cmd)

#             # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
#             system_config = np.flip(I_packets[0]['data'][20:24])
#             system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
#             burst_config['burst_pulses'] = int(system_config[16:24],base=2)

#         else:
#             print("Using manually-assigned burst command")
#             burst_config = decode_burst_command([96,0,0])
#             burst_config['burst_pulses'] = 1;

#         # Reassemble bytestreams using packet metadata:

#         # Loop through all packets to get the maximum data index:        
#         max_E_ind = max([p['start_ind'] + p['bytecount'] for p in filter(lambda packet: packet['exp_num'] == e_num, E_packets)])
#         max_B_ind = max([p['start_ind'] + p['bytecount'] for p in filter(lambda packet: packet['exp_num'] == e_num, B_packets)])
#         # max_G_ind = max([p['start_ind'] + p['bytecount'] for p in filter(lambda packet: packet['exp_num'] == e_num, G_packets)])
        
#         print("max E ind is:", max_E_ind, "max B ind is:", max_B_ind)
        
#         # Preallocate some space; we'll truncate it later.
#         E_data = np.empty(max_E_ind)
#         B_data = np.empty(max_B_ind)
#         G_data = np.empty(512*len(G_packets))
#         E_data[:] = np.nan; B_data[:] = np.nan; G_data[:] = np.nan;

#         print("reassembling E")


        
#         for p in filter(lambda packet: packet['exp_num'] == e_num, E_packets):
            
#             E_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']
            
#         print("reassembling B")
#         for p in filter(lambda packet: packet['exp_num'] == e_num, B_packets):
#             B_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

#         print("reassembling GPS")
#         for p in filter(lambda packet: packet['exp_num'] == e_num, G_packets):
#             G_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']


#         # Truncate trailing nans
#         # casting to uint8 is desirable, but also nukes the other nans... Eh.
#         E_data = remove_trailing_nans(E_data)#.astype('uint8')
#         B_data = remove_trailing_nans(B_data)#.astype('uint8')
#         G_data = remove_trailing_nans(G_data)#.astype('uint8')
#         # print(f"E has {np.sum(np.isnan(E_data))} nans")
#         # print(f"B has {np.sum(np.isnan(B_data))} nans")
#         # Juggle the 8-bit values around
#         if burst_config['TD_FD_SELECT']==1:
#             print("Selected time domain")
#             E = TD_reassemble(E_data)
#             B = TD_reassemble(B_data)


#         if burst_config['TD_FD_SELECT']==0:
#             print("seleced frequency domain")
#             E = FD_reassemble(E_data)
#             B = FD_reassemble(B_data)


#         # Decode any GPS data we might have
#         G = decode_GPS_data(G_data)
#         # print(G)

#         outs['E'] = E.astype('int16')
#         outs['B'] = B.astype('int16')
#         outs['G'] = G
#         outs['config'] = burst_config

#         # Generate time (and frequency) axis vectors for convenience
#         system_delay_samps_TD = 73;    
#         system_delay_samps_FD = 200;

#         # Construct the appropriate time and frequency axes
#         if burst_config['TD_FD_SELECT']==1:
#             # Time domain burst

#             # Get the equivalent sample rate, if decimated
#             if burst_config['DECIMATE_ON']==1:
#                 fs_equiv = 80000./burst_config['DECIMATION_FACTOR']
#             else:
#                 fs_equiv = 80000.
                
#             # Seconds from the start of the burst
#             t_axis = np.array([(np.arange(burst_config['SAMPLES_ON']))/fs_equiv +\
#                           (k*(burst_config['SAMPLES_ON'] + burst_config['SAMPLES_OFF']))/fs_equiv for k in range(burst_config['burst_pulses'])]).ravel()

#             # Add in system delay 
#             t_axis += system_delay_samps_TD/fs_equiv        
#             outs['t_axis'] = t_axis

#         if burst_config['TD_FD_SELECT']==0:

#             # Frequency-domain time axis
#             nfft = 1024
#             scale_factor = nfft/2./80000.
#             t_axis = np.array([(np.arange(burst_config['FFTS_ON']))/scale_factor +\
#                           (k*(burst_config['FFTS_ON'] + burst_config['FFTS_OFF']))/scale_factor for k in range(burst_config['burst_pulses'])]).ravel()
            
#             t_axis += system_delay_samps_FD/fs_equiv        
#             outs['t_axis'] = t_axis

#             # Frequency axis
#             f_axis = []
#             seg_length = nfft/2/16
#             for i, v in enumerate(burst_config['BINS']):
#                 if v=='1':
#                     f_axis.append([np.arange(seg_length)+seg_length*i])

#             f_axis = (40000/(nfft/2))*np.array(f_axis).ravel()

#             outs['f_axis'] = f_axis

#         out_list.append(outs)
#     return out_list


def decode_burst_data(packets, data_dict):

    # Select burst packets
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    I_packets     = sorted(I_packets, key = lambda p: p['header_timestamp'])
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    # burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    stats = decode_status(I_packets)
    for s in stats:
        print(s)

    # # -------- arrival time debugging plot -------
    # fig, ax = plt.subplots(1,1)
    # taxis = np.arange(len(burst_packets))    
    # tstamps = np.array([p['header_timestamp'] for p in burst_packets])
    # dtypes  = np.array([p['dtype'] for p in burst_packets])
    # ax.plot(taxis[dtypes=='E'], tstamps[dtypes=='E'],'b.', label='E')
    # ax.plot(taxis[dtypes=='B'], tstamps[dtypes=='B'],'r.', label='B')
    # ax.plot(taxis[dtypes=='G'], tstamps[dtypes=='G'],'g.', label='G')
    # ax.hlines([p['header_timestamp'] for p in I_packets], 0, len(burst_packets))
    # ax.legend()
    # ax.set_xlabel('arrival index')
    # ax.set_ylabel('timestamp')
    # plt.show()
    # print(np.unique([p['exp_num'] for p in burst_packets]))
    # # --------------------------------------------

    # Sort packets into data_dict to combine with previous data
    # for p in (E_packets + B_packets + G_packets):
    for p in burst_packets:
        data_dict[p['exp_num']].append(p)

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
    for IA, IB in zip(I_packets[0:-1], I_packets[1:]):
        ta = IA['header_timestamp']# - 1
        tb = IB['header_timestamp']# + 1
        
    #     # Let's confirm that the burst command is the same within each status packet:        
        IA_cmd = np.flip(IA['data'][12:15])
        IB_cmd = np.flip(IB['data'][12:15])

        # Skip any pairs with different burst commands (this might be questionable...)
        if any(IA_cmd != IB_cmd):
            continue
        for e_num in data_dict.keys():
            
            packets_in_time_range = list(filter(lambda p: p['header_timestamp'] >= ta and p['header_timestamp'] <= tb, data_dict[e_num]))           
            if packets_in_time_range:
                print(f'------ exp num {e_num} ------')
                print("status packet times:",datetime.datetime.utcfromtimestamp(ta),datetime.datetime.utcfromtimestamp(tb))

                # Ok! Now we have a list of packets, all with a common experiment number, 
                # in between two status packets, each with have the same burst command.
                # Ideally, this should be a complete set of burst data. Let's try processing it!

                # Get burst configuration parameters:
                cmd = np.flip(IA['data'][12:15])
                burst_config = decode_burst_command(cmd)

                # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
                system_config = np.flip(IA['data'][20:24])
                system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
                burst_config['burst_pulses'] = int(system_config[16:24],base=2)

                print(burst_config)

                processed = process_burst(packets_in_time_range, burst_config)
                completed_bursts.append(processed)

                # TODO: remove processed packets, return unused packets to be used later


    return completed_bursts

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
        n_samples = int(2*2*(burst_config['FFTS_ON'])*2*seg_length*burst_config['BINS'].count('1'))


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
    G = decode_GPS_data(G_data)
    print(G)
    outs = dict()
    outs['E'] = E
    outs['B'] = B
    outs['G'] = G
    outs['config'] = burst_config

    return outs

# 
            # if len(packets_in_time_range) > 100:
            # print("exp num",e_num,len(list(filter(lambda p: p['header_timestamp'] >= ta and p['header_timestamp'] <= tb, cur_packets))))
            # packet_times = [IP['header_epoch_sec'] + IP['header_ns']*1e-9 for IP in cur_packets]
            # filtered_packets = cur_packets[packet_times > ta and packet_times < tb]
    #     print("status found at time ",reference_date + datetime.timedelta(seconds=IP['header_epoch_sec']))
    #     # Loop through all saved experiment numbers:
    #     status_time = IP['header_epoch_sec'] + IP['header_ns']*1e-9 - 1
    #     print(status_time)
    #     for e_num, cur_packets in data_dict.items():
    #         print(len(list(filter(lambda packet: packet['header_epoch_sec'] + packet['header_ns']*1e-9 >= status_time, cur_packets))))


    # Run through the list and look for complete bursts:
    # for e_num, cur_packets in data_dict.items():
    #     print(f"analyzing {len(cur_packets)} packets for experiment number {e_num}")
    #     # Do we have a status packet?
    #     I_packets = list(filter(lambda p: (p['dtype'] == 'I'), cur_packets))
    #     if not I_packets:
    #         print("No echoed command found for exp num",e_num)
    #     else:
    #         print("Found echoed burst command for exp num",e_num)

    #         cmd = np.flip(I_packets[0]['data'][12:15])
    #         burst_config = decode_burst_command(cmd)

    #         # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
    #         system_config = np.flip(I_packets[0]['data'][20:24])
    #         system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
    #         burst_config['burst_pulses'] = int(system_config[16:24],base=2)

    #         print(burst_config)

    #         if burst_config['TD_FD_SELECT']==1:
    #             # Initialize for time domain
    #             n_samples = 2*burst_config['SAMPLES_ON']*burst_config['burst_pulses'] # how many 8-bit values should we get?
    #         elif burst_config['TD_FD_SELECT']==0:
    #             # Initialize for frequency domain
    #             seg_length = nfft/2/16 # number of FFTs within each "bin"
    #             n_samples = 2*burst_config['FFTS_ON']*2*seg_length*sum(burst_config['bins'])

    #         E_data = np.zeros(n_samples)*np.nan
    #         B_data = np.zeros(n_samples)*np.nan
    #         G_data = np.zeros(180*burst_config['burst_pulses'])*np.nan # this might overrun...


    #         print("reassembling E")
            
    #         for p in filter(lambda packet: packet['dtype'] == 'E', cur_packets):
    #             # print(p)
    #             E_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    #         print("reassembling B")
    #         for p in filter(lambda packet: packet['dtype'] == 'B', cur_packets):
    #             B_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    #         print("reassembling GPS")
    #         for p in filter(lambda packet: packet['dtype'] == 'G', cur_packets):
    #             G_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    #         # Do we have everything? 
    #         print(np.sum(np.isnan(E_data)), np.sum(~np.isnan(E_data)))
    #         if not (any(np.isnan(E_data)) or any(np.isnan(B_data)) or any(np.isnan(G_data))):
    #             print('Complete burst! Let''s decode it!')

    #             # Process data
    #             # Remove processed packets
    #             # Return completed data and unused packets


if __name__ == '__main__':

    with open('packets.pkl','rb') as f:
        packets = pickle.load(f)


    stats = decode_status(packets)
    for s in stats:
        print(s)
    outs = decode_burst_data(packets)
    print(outs)

    # with open('burst_raw.pkl','wb') as f:
    #     pickle.dump(outs, f)