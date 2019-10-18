import numpy as np
import matplotlib.pyplot as plt
import pickle
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal



def plot_survey_data(S_data, filename="survey_data.pdf"):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Plots survey data as PDFs

    inputs: 
        S_data: a list of dictionaries, as returned from decode_survey_data.py
                Each dictionary represents a single column of the survey product.
                A time axis will be constructed using the timestamps within each
                dictionary.
        filename: The filename to save
    outputs:
        saved images; format is defined by the suffix of filename
    '''

    # Assemble into grids:
    E = []
    B = []
    T = []
    F = np.arange(512)*40000/512;
    for S in S_data:
        if S['GPS'] is not None:
            T.append(S['GPS']['time'])
        else:
            T.append(np.NaN)

        E.append(S['E_data'])
        B.append(S['B_data'])


    E = np.array(E); B = np.array(B); T = np.array(T)


    fig = plt.figure()
    gs = GridSpec(2, 2, width_ratios=[20, 1])
    ax1 = fig.add_subplot(gs[0,0])
    ax2 = fig.add_subplot(gs[1,0])
    cbax = fig.add_subplot(gs[:,1])

    # survey_fullscale = 10*np.log10(pow(2,32))

    # # This is how we scaled the data in the Matlab code... I believe this maps the 
    # # VPM values (8-bit log scaled ints) to a log scaled amplitude.
    # E_data = 10*np.log10(pow(2,E_data/8)) - survey_fullscale
    # B_data = 10*np.log10(pow(2,B_data/8)) - survey_fullscale
    # 
    # (This is where we might bring in a real-world calibration factor)
    
    dates_formatter = mdates.DateFormatter("%m/%d")



    clims = [0,255] #[-80,-40]
    
    # Plot E data
    p1 = ax1.pcolorfast(E.T, vmin=clims[0], vmax=clims[1])
    p2 = ax2.pcolorfast(B.T, vmin=clims[0], vmax=clims[1])
    cb = plt.colorbar(p1, cax = cbax)
    cb.set_label('Raw value [0-255]')


    ax1.set_xticklabels([])
    ax1.set_yticks([0,128, 256, 384, 512])
    ax1.set_yticklabels([0,10,20,30,40])
    ax2.set_yticks([0,128, 256, 384, 512])
    ax2.set_yticklabels([0,10,20,30,40])
    formatted_xticklabels = [x.strftime("%H:%M:%S") for x in T]
    ax2.set_xticklabels(formatted_xticklabels)
    fig.autofmt_xdate()
    ax2.set_xlabel("Time (H:M:S) on \n%s"%T[0].strftime("%Y-%m-%d"))

    ax1.set_ylabel('E channel\nFrequency [kHz]')
    ax2.set_ylabel('B channel\nFrequency [kHz]')


    gs.tight_layout(fig)
    
    plt.show()
    fig.savefig(filename, bbox_inches='tight')



if __name__ == '__main__':

    print("hey")
    # Load decoded data:
    with open("decoded_data.pkl","rb") as f:
        d = pickle.load(f)
    print(d.keys())

    S_data = d['survey']

    plot_survey_data(S_data, "survey_data.pdf")