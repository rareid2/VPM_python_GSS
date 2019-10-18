import numpy as np
import pickle
import datetime
import matplotlib.pyplot as plt

from decode_packets import find_sequence
from decode_GPS_data import decode_GPS_data


def decode_survey_data(packets):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Gathers and reassembles any "survey" data contained within a set of packets.

    inputs: 
        packets: A list of "packet" dictionaries, as returned from decode_packets.py
    outputs:
        A list of dictionaries:
        Each dictionary is a single survey column, and contains the following fields:
            E_data: The electric field data, corresponding to averaged, log-scaled
                    magnitudes of the onboard FFT
            B_data: The magnetic field data, corresponding to averaged, log-scaled
                    magnitudes of the onboard FFT
            GPS:    A dictionary of decoded GPS data, corresponding to the end of
                    the current survey product
    '''
    S_packets = list(filter(lambda packet: packet['dtype'] == 'S', packets))

    if len(S_packets) == 0:
        print("no survey data present!")
        return

    # These will roll over every 256 survey columns... need to deal with that
    # in this search. For now, just assume they're unique
    e_nums = np.unique([x['exp_num'] for x in S_packets])
    # print(e_nums)

    LCS_board_present = False # And it never should be!

    survey_packet_length = 1260
    gps_length = 180
    survey_header = np.array([205, 171, 33, 67])
    survey_footerooter = np.array([137, 103, 33, 67])

    # survey_fullscale = 10*np.log10(pow(2,32))

    # Index kernels
    gps_index = np.arange(len(survey_header),len(survey_header) + gps_length).astype('int')
    # The indices of the BBR data -- four-byte interleaved (1,2,3,4),(9,10,11,12),(17,18,19,20)...
    bbr_index_noLCS = np.array([np.arange(4) + 4 + k*8 for k in range(128)]).ravel().astype('int')
    gps_index += bbr_index_noLCS[-1] + 1

    # Gather and reassemble the 3-ish survey (system) packets into a single survey (product) packet
    S_data = []
    for e_num in e_nums:
        
        # Reassemble into a single survey data packet
        cur_data = np.zeros(survey_packet_length)
        for p in filter(lambda packet: packet['exp_num'] == e_num, S_packets):
            cur_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

            E_data = cur_data[bbr_index_noLCS]
            B_data = cur_data[bbr_index_noLCS + 4]
            G_data = cur_data[gps_index].astype('uint8')

        # # This is how we scaled the data in the Matlab code... I believe this maps the 
        # # VPM values (8-bit log scaled ints) to a log scaled amplitude.
        # E_data = 10*np.log10(pow(2,E_data/8)) - survey_fullscale
        # B_data = 10*np.log10(pow(2,B_data/8)) - survey_fullscale

        G = decode_GPS_data(G_data)
        if G is not None:
            print(G['time'])
        
        d = dict()
        d['GPS'] = G
        d['E_data'] = E_data
        d['B_data'] = B_data
        # d['G_raw'] = G_data.astype('int')
        S_data.append(d)

    return S_data

if __name__ == '__main__':


    with open('packets.pkl','rb') as f:
        packets = pickle.load(f)

    S_data = decode_survey_data(packets)

    with open("survey_data.pkl",'wb') as f:
        pickle.dump(S_data, f)

    # fig, ax = plt.subplots(1,1)
