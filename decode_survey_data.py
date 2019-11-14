import numpy as np
import pickle
import datetime
import matplotlib.pyplot as plt
import logging

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

    # leap_seconds = 18  # GPS time does not account for leap seconds; as of ~2019, GPS leads UTC by 18 seconds.
    # reference_date = datetime.datetime(1980,1,6,0,0, tzinfo=datetime.timezone.utc) - datetime.timedelta(seconds=leap_seconds)
    logger = logging.getLogger(__name__)

    S_packets = list(filter(lambda packet: packet['dtype'] == 'S', packets))
    # Sort by arrival time
    S_packets = sorted(S_packets, key=lambda p: p['header_epoch_sec'] + p['header_ns']*1e-9)

    if len(S_packets) == 0:
        logger.info("no survey data present!")
        return [], []

    # These will roll over every 256 survey columns... need to deal with that
    # in this search. For now, just assume they're unique

    
    # ax.plot(np.diff([x['exp_num'] for x in S_packets]),'.')
    # plt.show()
    e_nums = np.unique([x['exp_num'] for x in S_packets])

    logging.debug(f'available survey experiment numbers: {e_nums}')

    survey_packet_length = 1212

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
    complete_surveys = []
    unused = []
    separation_time = 0.5  # seconds
    for e_num in e_nums:

        # Reassemble into a single survey data packet
        cur_packets   = list(filter(lambda packet: packet['exp_num'] == e_num, S_packets))

        # Divide this list up into segments with nearby arrival times:
        arrival_times = [p['header_epoch_sec'] + p['header_ns']*1e-9 for p in cur_packets]
        # Find any significant time differences
        splits = np.where(np.diff(arrival_times) > separation_time)[0] + 1  
        # append the first and last indexes to the list, to give us pairs of indexes to slice around
        splits = np.insert(np.append(splits,[len(cur_packets)]),0,0) 

        # Iterate over sub-lists of packets, as divided by splits:
        for s1,s2 in zip(splits[0:-1],splits[1:]):
            # Start with all nans
            cur_data = np.zeros(survey_packet_length)*np.nan
            # Insert each packets' payload
            for p in cur_packets[s1:s2]:
                cur_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']
            # Did we get a full packet? 
            if np.sum(np.isnan(cur_data)) == 0:
                # Complete packet!
                
                E_data = cur_data[bbr_index_noLCS]
                B_data = cur_data[bbr_index_noLCS + 4]
                G_data = cur_data[gps_index].astype('uint8')

                G = decode_GPS_data(G_data)

                d = dict()
                d['GPS'] = G
                d['E_data'] = E_data.astype('uint8')
                d['B_data'] = B_data.astype('uint8')
                # d['header_epoch_sec'] = cur_packets[s1]['header_epoch_sec']
                d['header_timestamp'] = cur_packets[s1]['header_timestamp']
                d['exp_num'] = e_num
                # d['header_timestamp'] = (reference_date + \
                #     datetime.timedelta(seconds=cur_packets[s1]['header_epoch_sec'] + cur_packets[s1]['header_ns']*1e-9)).timestamp()
                S_data.append(d)


                # print("header: ",datetime.datetime.utcfromtimestamp(d['header_timestamp']))
                # if G is not None:
                #     print(datetime.datetime.utcfromtimestamp(G[0]['timestamp']))

            else:
                # If not, put the unused packets aside, so we can possibly
                # combine with packets from other files
                unused.extend(cur_packets[s1:s2])

    # Send it
    logger.info(f'Recovered {len(S_data)} survey products, leaving {len(unused)} unused packets')
    return S_data, unused

if __name__ == '__main__':


    with open('packets_158-8490-408.pkl','rb') as f:
        packets = pickle.load(f)

    S_data, unused = decode_survey_data(packets)

    with open("survey_data.pkl",'wb') as f:
        pickle.dump(S_data, f)

    # fig, ax = plt.subplots(1,1)
