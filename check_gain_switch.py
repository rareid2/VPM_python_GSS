import numpy as np
import pickle
from scipy.io import loadmat
import os
import json
import datetime
import matplotlib.pyplot as plt
from file_handlers import read_survey_XML

S_data = read_survey_XML('/home/rileyannereid/Downloads/VPM_survey_data_2020-05-11.xml')

S_data = sorted(S_data, key = lambda f: f['header_timestamp'])

S_with_GPS = list(filter(lambda x: (('GPS' in x) and 
                                        ('timestamp' in x['GPS'][0]) and
                                        ('lat' in x['GPS'][0]) and
                                        ('horiz_speed' in x['GPS'][0])), S_data))
S_with_GPS = sorted(S_with_GPS, key = lambda f: f['GPS'][0]['timestamp'])
T_gps = np.array([x['GPS'][0]['timestamp'] for x in S_with_GPS])
dts_gps = np.array([datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc) for x in T_gps])

# Build arrays
E = []
E_other = []
B = []
T = []
cal = []
F = np.arange(512)*40/512;
bus_timestamps=False

# # Only plot survey data if we have GPS data to match
if bus_timestamps:
    for S in S_data:
        T.append(S['header_timestamp'])
        E.append(S['E_data'])
        B.append(S['B_data'])
else:
    # Sort using payload GPS timestamp (rounded to nearest second.
    # Ugh, why didn't we just save a local microsecond counter... do that on CANVAS please)
    for S in S_with_GPS:
        T.append(S['GPS'][0]['timestamp'])
        
        B.append(S['B_data'])

        # cal info
        #gain = S['gain']
        #survey_type = S['survey_type']

        #if gain == 'high':
        #    gain_f = 1
        #else: # low gain
        #    gain_f = 10
        #if survey_type == 'short':
        #    shift = 55
        #else: # long survey
        #   shift = 58
        
        # append the calibrated the data
        E.append( 10 * np.log10( 10 * 2**(S['E_data'] / 8) ) - 58 )
        E_other.append(10 * np.log10( 1 * 2**(S['E_data'] / 8) ) - 58)
            
    T = np.array(T)

    dates = np.array([datetime.datetime.utcfromtimestamp(t) for t in T])
    for di, d in enumerate(dates):
        if di == len(dates) - 1:
            continue
        dt = dates[di+1] - d
        #print(dt.seconds, d)


    # -----------------------------------
    # Spectrograms
    # -----------------------------------
    E = np.array(E); B = np.array(B); T = np.array(T);

    plt.plot(F, E[1890], label=' (low gain)')
    plt.plot(F, E[1892], label='after switch (low gain)')
    print(dates[1892])
    plt.plot(F, E_other[1892], label='after switch (high gain)')

    #plt.plot(F, E_other[1890], label='assuming low')

    #plt.plot(F, E[1892], label='high')
    #plt.plot(F, E_other[1892], label='low')
    plt.title('spectrogram at ' + str(dates[1890]) + ' to ' + str(dates[1891]))
    plt.legend()
    plt.show()
    plt.close()
