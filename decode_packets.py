import numpy as np
import pickle
from scipy.io import loadmat
import os
import struct
import datetime
import logging


def find_sequence(arr,seq):
    '''
    Find any instances of a sequence seq in 1d array arr.
    Returns an array of indexes corresponding to the first value in the sequence.
    '''
    # Store sizes of input array and sequence
    Na, Nseq = arr.size, seq.size
    # Range of sequence
    r_seq = np.arange(Nseq)
    # Create a 2D array of sliding indices across the entire length of input array.
    # Match up with the input sequence & get the matching starting indices.
    M = (arr[np.arange(Na-Nseq+1)[:,None] + r_seq] == seq).all(1)
    inds = np.where(M)[0]
    return(inds)


def decode_packets(data, fname=None):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.10.2019
    Description:
        Parses a raw byte string from VPM; locates packets and calculates
        checksums; unescapes 7E/7D characters; decodes various metadata.
    inputs: data -- a 1d numpy array of 8-bit unsigned integers
    outputs:
        a list of decoded packets:
        Each packet is a dictionary with the following fields:
        packet_data:        2d array of packet data (num_packets x data_segment_length)
        packet_start_index: Start index of the current data segment
        datatype:           Channel label. (Ascii 'S','E','B','L','G','I')
        experiment_number:  indicates the experiment to which packets belong to
        bytecounts:         length of actual data within packet_data
                            (i.e., when reassembling, place the current packet_data at
                            [packet_start_index(i):packet_start_index(i) + bytecounts(i)]
        packet_lengths:     length of each packet, including headers, but after escaping
        verify:             received checksum - calculated checksum.
                            Should be all zeros unless we have some corruption happening.
    '''
    logger = logging.getLogger(__name__)

    # Packet indices and lengths (set in payload firmware)
    PACKET_SIZE = 512
    DATA_SEGMENT_LENGTH = PACKET_SIZE - 8
    PACKET_COUNT_INDEX = 1
    DATA_TYPE_INDEX = 5
    EXPERIMENT_INDEX = 6
    DATA_START_INDEX = 7
    DATA_END_INDEX = DATA_START_INDEX + DATA_SEGMENT_LENGTH
    CHECKSUM_INDEX = PACKET_SIZE - 2

    CTCSS_HEADER_LEN = 26

    leap_seconds = 18  # GPS time does not account for leap seconds; as of ~2019, GPS leads UTC by 18 seconds.
    reference_date = datetime.datetime(1980,1,6,0,0, tzinfo=datetime.timezone.utc) - datetime.timedelta(seconds=leap_seconds)


    # Find all packet start indices
    p_inds_pre_escape = np.array(sorted(np.where(data==0x7E)))
    p_length_pre_escape = np.diff(p_inds_pre_escape)

    # Select only the valid packet start indices
    p_start_inds = p_inds_pre_escape[np.where(p_length_pre_escape == (PACKET_SIZE - 1))]
    logger.info(f"found {len(p_start_inds)} valid packets")
    
    # Escape characters, and move packets into a list (since their length now varies)
    packets = [];
    checksum_failure_counter = 0

    # for k in np.arange(-6, 20):
    for x, pind in enumerate(p_start_inds):
        try:
            cur_packet = np.copy(data[pind:pind+PACKET_SIZE].astype('uint8'))
            # cur_packet   = data[pind:pind+PACKET_SIZE]
            ctcss_header = np.copy(data[pind-CTCSS_HEADER_LEN:pind]).astype('uint8')
            # print(['{0:X}'.format(x) for x in data[pind:pind + EXPERIMENT_INDEX + 3]])

            # grab data from the CTCSS header
            C_packet_length = struct.unpack('>I', ctcss_header[0:4].tobytes())[0] # 534
            C_component_ID  = struct.unpack('>B', ctcss_header[5:6].tobytes())[0] # 34
            C_interface_ID  = struct.unpack('>B', ctcss_header[6:7].tobytes())[0] # 1
            C_message_ID    = struct.unpack('>B', ctcss_header[7:8].tobytes())[0] # 2
            C_epoch_seconds = struct.unpack('>I', ctcss_header[8:12].tobytes())[0]
            C_nanoseconds   = struct.unpack('>I', ctcss_header[12:16].tobytes())[0]
            C_reboot_count  = struct.unpack('>H', ctcss_header[16:18].tobytes())[0]


            # Check if the bytecount or checksum fields were escaped
            check_escaped = (cur_packet[PACKET_SIZE - 2]!=0)*1
            count_escaped = (cur_packet[PACKET_SIZE - 4]!=0)*1

            # Calculate the checksum (on the unescaped data):
            checksum_calc = sum(cur_packet[2:CHECKSUM_INDEX - 1])%256

            # Un-escape the packet (Destructive)
            esc1_inds = find_sequence(cur_packet,np.array([0x7D, 0x5E])) # [7D, 5E] -> 7E
            cur_packet[esc1_inds] =  0x7E
            cur_packet = np.delete(cur_packet, esc1_inds + 1) 
            esc2_inds = find_sequence(cur_packet,np.array([0x7D, 0x5D])) # [7D, 5D] -> 7D
            cur_packet = np.delete(cur_packet, esc2_inds + 1)


            # Get the new indices of the checksum and bytecount fields
            packet_length_post_escape = len(cur_packet)
            checksum_index = packet_length_post_escape + check_escaped - 3
            bytecount_index= packet_length_post_escape + check_escaped + count_escaped - 6
     
            # Decode metadata fields
            packet_start_index = (cur_packet[PACKET_COUNT_INDEX]     << 24) + \
                                 (cur_packet[PACKET_COUNT_INDEX + 1] << 16) + \
                                 (cur_packet[PACKET_COUNT_INDEX + 2] << 8)  + \
                                  cur_packet[PACKET_COUNT_INDEX + 3]

            datatype = chr(cur_packet[DATA_TYPE_INDEX]) # works!
            experiment_number = cur_packet[EXPERIMENT_INDEX]
            # print(experiment_number)
            bytecount = 256*cur_packet[bytecount_index] + cur_packet[bytecount_index + 1]
            checksum = cur_packet[checksum_index]

            if (checksum - checksum_calc) != 0:
                checksum_failure_counter += 1
                # print('invalid checksum at packet # %d'%x)
                # print(cur_packet)

            # Pack the decoded packet into a dictionary, and add it to the list
            # (maybe there's a nicer data structure for this - but this is probably the most general case)
            p = dict()
            p['data'] = np.array(cur_packet[DATA_START_INDEX:(bytecount + DATA_START_INDEX)], dtype='uint8').tolist()
            p['start_ind'] = packet_start_index
            p['dtype'] = datatype
            p['exp_num'] = experiment_number
            p['bytecount'] = bytecount
            p['checksum_verify'] = (checksum - checksum_calc)==0
            p['packet_length'] = packet_length_post_escape
            p['fname'] = fname
            p['header_ns'] = C_nanoseconds
            p['header_epoch_sec'] = C_epoch_seconds
            p['header_reboots'] = C_reboot_count
            p['header_timestamp'] = (reference_date + datetime.timedelta(seconds=C_epoch_seconds + C_nanoseconds*1e-9)).timestamp()
                
            packets.append(p)


        except:
            logger.warning('exception at packet # %d',x)
        
    if checksum_failure_counter > 0:
        logger.warning(f'--------------- {checksum_failure_counter} failed checksums ---------------')

    return packets


if __name__ == '__main__':

    # inp_datafile = '/Users/austin/Dropbox/VPM working directory/Python GSS/Data from AFRL, Feb 2015/Test 2-caltone.mat'
    # mat_datafile = loadmat(inp_datafile, squeeze_me=True)
    # mat_data = mat_datafile["outData_tones"]


    # print('decoding packets...')
    # packets = decode_packets(mat_data)

    # print('dumping to packets.pkl...')

    # with open('packets.pkl','wb') as f:
    #     pickle.dump(packets, f)



    data_root = 'Data/matlab/decimation_tests_2014/'# 'Data/ditl_cal'
    d = os.listdir(data_root)
    tlm_files = sorted([x for x in d if x.endswith('.tlm')])

    raw_data = []
    for fname in tlm_files:
        with open(os.path.join(data_root, fname),'rb') as f:
            cur_data = np.fromfile(f,dtype='uint8')
            raw_data.append(cur_data)

    data = np.concatenate(raw_data).ravel()
    print(np.shape(data))

    packets = decode_packets(data)

