import numpy as np
import pickle
import scipy.stats
from decode_burst_command import decode_burst_command
from decode_GPS_data import decode_GPS_data

def remove_trailing_nans(arr1d):
    ''' Trims off the trailing NaNs of a vector.'''
    notnans = np.flatnonzero(~np.isnan(arr1d))
    if notnans.size:
        # Trim leading and trailing:
#         trimmed = arr1d[notnans[0]: notnans[-1]+1]  # slice from first not-nan to the last one
        # Trim trailing only
        trimmed = arr1d[:notnans[-1]+1]  # slice from first not-nan to the last one
    else:
        trimmed = np.zeros(0)
    return trimmed

def TD_reassemble(vec):
    ''' Rearranges a byte string into 16-bit values (packed as a double),
     following time-domain interleaving'''
    re = vec[:len(vec) - (len(vec)%4)].astype('uint8')
    re = np.reshape(re, [int(len(re)/4),4])
    re = np.stack([(re[:,0] + 256*re[:,1]).astype('int16'), (re[:,2] + 256*re[:,3]).astype('int16')],axis=1)
    re = re.ravel()
    re = re/pow(2,15)
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
    re = re/pow(2,15)
    return re


def decode_burst_data(packets, burst_cmd = None):

    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))

    # Get all unique experiment numbers for this set of packets 
    # (chances are real good that we'll only have 1 or 2 unique numbers)
    avail_exp_nums = np.unique([x['exp_num'] for x in E_packets + B_packets])
    e_num = scipy.stats.mode(avail_exp_nums[0])[0][0] # Pick the one we have the most of
    
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
        burst_config['burst_pulses'] = int(system_config[16:24],8)

    else:
        print("Using manually-assigned burst command")
        burst_config = decode_burst_command(burst_cmd)
        burst_config['burst_pulses'] = 1;

    # Reassemble bytestreams using packet metadata:
    # Preallocate some space; we'll truncate it later.
    E_data = np.empty(512*len(E_packets))
    B_data = np.empty(512*len(B_packets))
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
    E_data = remove_trailing_nans(E_data).astype('uint8')
    B_data = remove_trailing_nans(B_data).astype('uint8')
    G_data = remove_trailing_nans(G_data).astype('uint8')

    # Juggle the 8-bit values around
    if burst_config['TD_FD_SELECT']==1:
        print("Selected time domain")
        E = TD_reassemble(E_data)
        B = TD_reassemble(E_data)
    if burst_config['TD_FD_SELECT']==0:
        print("seleced frequency domain")
        E = FD_reassemble(E_data)
        B = FD_reassemble(E_data)

    # Decode any GPS data we might have
    G = decode_GPS_data(G_data)
    print(G)
if __name__ == '__main__':

    with open('packets.pkl','rb') as f:
        packets = pickle.load(f)

    decode_burst_data(packets)

    # with open('burst_raw.pkl','wb') as f:
    #     pickle.dump(outs, f)