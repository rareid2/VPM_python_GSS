import numpy as np
import pickle
import scipy.stats
from decode_burst_command import decode_burst_command
from decode_GPS_data import decode_GPS_data
from decode_status import decode_status

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
    re = re.ravel()
    # re = re/pow(2,15)
    return re
    
def FD_reassemble(vec):
    ''' Rearranges a byte string into 16-bit values (packed as a complex double),
    following time-domain interleaving.
    Untested as of 10/11/2019, but follows the Matlab code! I need some FD data to try it with.
    '''
    re = vec[:len(vec) - (len(vec)%4)].astype('uint8')
    re = np.reshape(re, [int(len(re)/4),4])
    re = np.stack([(re[:,0] + 256*re[:,1]).astype('int16'), (re[:,2] + 256*re[:,3]).astype('int16')],axis=1)
    re = re[:,0] + 1j*re[:,1]
    # re = re/pow(2,15)
    return re


def decode_burst_data(packets, burst_cmd = None):

    out_list = []

    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))

    # Get all unique experiment numbers for this set of packets 
    # (chances are real good that we'll only have 1 or 2 unique numbers)
    avail_exp_nums = np.unique([x['exp_num'] for x in E_packets + B_packets])
    print("available burst experiment numbers:",avail_exp_nums)
    # e_num = scipy.stats.mode(avail_exp_nums[0])[0][0] # Pick the one we have the most of
    for e_num in avail_exp_nums:
        
        outs = dict() # The output container

        # Do we have any corresponding status packets?
        # These are tagged with p['data'][3] == 'B', and are requested at 
        # either end of a burst. 
        I_packets = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
        
        # Grab the burst command from the first status packet.
        if I_packets:
            print("Using echoed burst command")
            cmd = np.flip(I_packets[0]['data'][12:15])
            burst_config = decode_burst_command(cmd)

            # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
            system_config = np.flip(I_packets[0]['data'][20:24])
            system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
            burst_config['burst_pulses'] = int(system_config[16:24],base=2)

        else:
            print("Using manually-assigned burst command")
            burst_config = decode_burst_command([96,0,0])
            burst_config['burst_pulses'] = 1;

        # Reassemble bytestreams using packet metadata:

        # Loop through all packets to get the maximum data index:        
        max_E_ind = max([p['start_ind'] + p['bytecount'] for p in filter(lambda packet: packet['exp_num'] == e_num, E_packets)])
        max_B_ind = max([p['start_ind'] + p['bytecount'] for p in filter(lambda packet: packet['exp_num'] == e_num, B_packets)])
        # max_G_ind = max([p['start_ind'] + p['bytecount'] for p in filter(lambda packet: packet['exp_num'] == e_num, G_packets)])
        
        print("max E ind is:", max_E_ind, "max B ind is:", max_B_ind)
        
        # Preallocate some space; we'll truncate it later.
        E_data = np.empty(max_E_ind)
        B_data = np.empty(max_B_ind)
        G_data = np.empty(512*len(G_packets))
        E_data[:] = np.nan; B_data[:] = np.nan; G_data[:] = np.nan;

        print("reassembling E")


        
        for p in filter(lambda packet: packet['exp_num'] == e_num, E_packets):
            
            E_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']
            
        print("reassembling B")
        for p in filter(lambda packet: packet['exp_num'] == e_num, B_packets):
            B_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

        print("reassembling GPS")
        for p in filter(lambda packet: packet['exp_num'] == e_num, G_packets):
            G_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']


        # Truncate trailing nans
        # casting to uint8 is desirable, but also nukes the other nans... Eh.
        E_data = remove_trailing_nans(E_data)#.astype('uint8')
        B_data = remove_trailing_nans(B_data)#.astype('uint8')
        G_data = remove_trailing_nans(G_data)#.astype('uint8')
        # print(f"E has {np.sum(np.isnan(E_data))} nans")
        # print(f"B has {np.sum(np.isnan(B_data))} nans")
        # Juggle the 8-bit values around
        if burst_config['TD_FD_SELECT']==1:
            print("Selected time domain")
            E = TD_reassemble(E_data)
            B = TD_reassemble(B_data)


        if burst_config['TD_FD_SELECT']==0:
            print("seleced frequency domain")
            E = FD_reassemble(E_data)
            B = FD_reassemble(B_data)


        # Decode any GPS data we might have
        G = decode_GPS_data(G_data)
        # print(G)

        outs['E'] = E.astype('int16')
        outs['B'] = B.astype('int16')
        outs['G'] = G
        outs['config'] = burst_config

        # Generate time (and frequency) axis vectors for convenience
        system_delay_samps_TD = 73;    
        system_delay_samps_FD = 200;

        # Construct the appropriate time and frequency axes
        if burst_config['TD_FD_SELECT']==1:
            # Time domain burst

            # Get the equivalent sample rate, if decimated
            if burst_config['DECIMATE_ON']==1:
                fs_equiv = 80000./burst_config['DECIMATION_FACTOR']
            else:
                fs_equiv = 80000.
                
            # Seconds from the start of the burst
            t_axis = np.array([(np.arange(burst_config['SAMPLES_ON']))/fs_equiv +\
                          (k*(burst_config['SAMPLES_ON'] + burst_config['SAMPLES_OFF']))/fs_equiv for k in range(burst_config['burst_pulses'])]).ravel()

            # Add in system delay 
            t_axis += system_delay_samps_TD/fs_equiv        
            outs['t_axis'] = t_axis

        if burst_config['TD_FD_SELECT']==0:

            # Frequency-domain time axis
            nfft = 1024
            scale_factor = nfft/2./80000.
            t_axis = np.array([(np.arange(burst_config['FFTS_ON']))/scale_factor +\
                          (k*(burst_config['FFTS_ON'] + burst_config['FFTS_OFF']))/scale_factor for k in range(burst_config['burst_pulses'])]).ravel()
            
            t_axis += system_delay_samps_FD/fs_equiv        
            outs['t_axis'] = t_axis

            # Frequency axis
            f_axis = []
            seg_length = nfft/2/16
            for i, v in enumerate(burst_config['BINS']):
                if v=='1':
                    f_axis.append([np.arange(seg_length)+seg_length*i])

            f_axis = (40000/(nfft/2))*np.array(f_axis).ravel()

            outs['f_axis'] = f_axis

        out_list.append(outs)
    return out_list

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