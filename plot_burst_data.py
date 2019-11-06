import numpy as np
import matplotlib.pyplot as plt
import pickle
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal

from matplotlib.colors import LinearSegmentedColormap
def parula_cm():
    '''Matlab's Parula colormap (the current default, looks pretty)
    '''
    cm_data = [[0.2081, 0.1663, 0.5292], [0.2116238095, 0.1897809524, 0.5776761905], 
    [0.212252381, 0.2137714286, 0.6269714286], [0.2081, 0.2386, 0.6770857143], 
    [0.1959047619, 0.2644571429, 0.7279], [0.1707285714, 0.2919380952, 
    0.779247619], [0.1252714286, 0.3242428571, 0.8302714286], 
    [0.0591333333, 0.3598333333, 0.8683333333], [0.0116952381, 0.3875095238, 
    0.8819571429], [0.0059571429, 0.4086142857, 0.8828428571], 
    [0.0165142857, 0.4266, 0.8786333333], [0.032852381, 0.4430428571, 
    0.8719571429], [0.0498142857, 0.4585714286, 0.8640571429], 
    [0.0629333333, 0.4736904762, 0.8554380952], [0.0722666667, 0.4886666667, 
    0.8467], [0.0779428571, 0.5039857143, 0.8383714286], 
    [0.079347619, 0.5200238095, 0.8311809524], [0.0749428571, 0.5375428571, 
    0.8262714286], [0.0640571429, 0.5569857143, 0.8239571429], 
    [0.0487714286, 0.5772238095, 0.8228285714], [0.0343428571, 0.5965809524, 
    0.819852381], [0.0265, 0.6137, 0.8135], [0.0238904762, 0.6286619048, 
    0.8037619048], [0.0230904762, 0.6417857143, 0.7912666667], 
    [0.0227714286, 0.6534857143, 0.7767571429], [0.0266619048, 0.6641952381, 
    0.7607190476], [0.0383714286, 0.6742714286, 0.743552381], 
    [0.0589714286, 0.6837571429, 0.7253857143], 
    [0.0843, 0.6928333333, 0.7061666667], [0.1132952381, 0.7015, 0.6858571429], 
    [0.1452714286, 0.7097571429, 0.6646285714], [0.1801333333, 0.7176571429, 
    0.6424333333], [0.2178285714, 0.7250428571, 0.6192619048], 
    [0.2586428571, 0.7317142857, 0.5954285714], [0.3021714286, 0.7376047619, 
    0.5711857143], [0.3481666667, 0.7424333333, 0.5472666667], 
    [0.3952571429, 0.7459, 0.5244428571], [0.4420095238, 0.7480809524, 
    0.5033142857], [0.4871238095, 0.7490619048, 0.4839761905], 
    [0.5300285714, 0.7491142857, 0.4661142857], [0.5708571429, 0.7485190476, 
    0.4493904762], [0.609852381, 0.7473142857, 0.4336857143], 
    [0.6473, 0.7456, 0.4188], [0.6834190476, 0.7434761905, 0.4044333333], 
    [0.7184095238, 0.7411333333, 0.3904761905], 
    [0.7524857143, 0.7384, 0.3768142857], [0.7858428571, 0.7355666667, 
    0.3632714286], [0.8185047619, 0.7327333333, 0.3497904762], 
    [0.8506571429, 0.7299, 0.3360285714], [0.8824333333, 0.7274333333, 0.3217], 
    [0.9139333333, 0.7257857143, 0.3062761905], [0.9449571429, 0.7261142857, 
    0.2886428571], [0.9738952381, 0.7313952381, 0.266647619], 
    [0.9937714286, 0.7454571429, 0.240347619], [0.9990428571, 0.7653142857, 
    0.2164142857], [0.9955333333, 0.7860571429, 0.196652381], 
    [0.988, 0.8066, 0.1793666667], [0.9788571429, 0.8271428571, 0.1633142857], 
    [0.9697, 0.8481380952, 0.147452381], [0.9625857143, 0.8705142857, 0.1309], 
    [0.9588714286, 0.8949, 0.1132428571], [0.9598238095, 0.9218333333, 
    0.0948380952], [0.9661, 0.9514428571, 0.0755333333], 
    [0.9763, 0.9831, 0.0538]]

    parula_map = LinearSegmentedColormap.from_list('parula', cm_data)
    return parula_map
    # For use of "viscm view"
    # test_cm = parula_map


def plot_burst_data(B_data, filename="burst_data.pdf"):
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 8 
    fig_height = 6
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 10,
              'font.size': 10,
              'legend.fontsize': 8,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------

    # A list of bursts!
    for burst in B_data:
    # for burst in [B_data[1]]:
        print(burst['config'])
        cfg = burst['config']
        if len(burst['G']) > 0:
            timestamp = burst['G'][0]['timestamp']  # This might be a list of timestamps for windowed bursts
            for g in burst['G']:
                print(datetime.datetime.utcfromtimestamp(g['timestamp']))
        else:
            timestamp = 0 #datetime.datetime(1970,1,1,0,0,0).timestamp()

        print(cfg)



        system_delay_samps_TD = 73;    
        system_delay_samps_FD = 200;
        fs = 80000;
        # cm = plt.cm.jet
        cm = parula_cm();


        if cfg['TD_FD_SELECT'] == 1:
            # Time domain mode
            fig = plt.figure()
            gs = GridSpec(2, 3, width_ratios=[20, 20, 1])
            E_TD = fig.add_subplot(gs[0,0])
            B_TD = fig.add_subplot(gs[1,0])
            E_FD = fig.add_subplot(gs[0,1])
            B_FD = fig.add_subplot(gs[1,1])
            cb1 = fig.add_subplot(gs[0,2])
            cb2 = fig.add_subplot(gs[1,2])




            # --------- Time domain plots  -----------
            td_lims = [-32768, 32768] #[-1,1]
            # Generate time axis


            # Construct the appropriate time and frequency axes
            # Get the equivalent sample rate, if decimated
            if cfg['DECIMATE_ON']==1:
                fs_equiv = 80000./cfg['DECIMATION_FACTOR']
            else:
                fs_equiv = 80000.

            # Seconds from the start of the burst
            t_axis = np.array([(np.arange(cfg['SAMPLES_ON']))/fs_equiv +\
                          (k*(cfg['SAMPLES_ON'] + cfg['SAMPLES_OFF']))/fs_equiv for k in range(cfg['burst_pulses'])]).ravel()

            # Add in system delay 
            t_axis += system_delay_samps_TD/fs_equiv        

            sec_on  = cfg['SAMPLES_ON']/fs_equiv
            sec_off = cfg['SAMPLES_OFF']/fs_equiv
            
            E_TD.plot(t_axis[0:len(burst['E'])], burst['E'])
            B_TD.plot(t_axis[0:len(burst['B'])], burst['B'])

            E_TD.set_ylim(td_lims)
            B_TD.set_ylim(td_lims)

            nfft=1024;
            overlap = 0.5
            window = 'hanning'

            

            # Insert nans into vector to account for "off" time sections
            E_td_spaced = []
            B_td_spaced = []
            
            for k in np.arange(cfg['burst_pulses']):
                E_td_spaced.append(burst['E'][k*cfg['SAMPLES_ON']:(k+1)*cfg['SAMPLES_ON']])
                E_td_spaced.append(np.ones(cfg['SAMPLES_OFF'])*np.nan)
                B_td_spaced.append(burst['B'][k*cfg['SAMPLES_ON']:(k+1)*cfg['SAMPLES_ON']])
                B_td_spaced.append(np.ones(cfg['SAMPLES_OFF'])*np.nan)


            E_td_spaced = np.concatenate(E_td_spaced).ravel()
            B_td_spaced = np.concatenate(B_td_spaced).ravel()

            
            clims = [-96, -20]

            # E spectrogram
            ff,tt, FE = scipy.signal.spectrogram(E_td_spaced/32768., fs=fs, window=window,
                        nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density')
            E_S_mag = 20*np.log10(np.sqrt(FE))
            E_S_mag[np.isinf(E_S_mag)] = -100
            print(np.min(E_S_mag), np.max(E_S_mag))
        #     pe = E_FD.pcolormesh(tt,ff,np.log10(E_S_mag), cmap = cm, shading='gouraud')
            pe = E_FD.pcolorfast(tt,ff/1000,E_S_mag, cmap = cm,  vmin=clims[0], vmax=clims[1])
            ce = plt.colorbar(pe, cax=cb1)

            # B spectrogram
            ff,tt, FB = scipy.signal.spectrogram(B_td_spaced/32768., fs=fs, window=window,
                        nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density')
            B_S_mag = 20*np.log10(np.sqrt(FB))
            B_S_mag[np.isinf(B_S_mag)] = -100
            print(np.min(B_S_mag), np.max(B_S_mag))
        #     pb = B_FD.pcolormesh(tt,ff, np.log10(B_S_mag), cmap = cm, shading='gouraud')
            pb = B_FD.pcolorfast(tt,ff/1000, B_S_mag, cmap = cm,  vmin=clims[0], vmax=clims[1])
            cb = plt.colorbar(pb, cax=cb2)

            E_TD.set_xticklabels([])
            E_FD.set_xticklabels([])

            E_TD.set_ylabel('E\nAmplitude')
            B_TD.set_ylabel('B\nAmplitude')
            E_FD.set_ylabel('Frequency [kHz]')
            B_FD.set_ylabel('Frequency [kHz]')
            B_TD.set_xlabel('Time [sec]')
            B_FD.set_xlabel('Time [sec]')

            ce.set_label('dB(sqrt(psd))')
            cb.set_label('dB(sqrt(psd))')

            fig.suptitle('Time-Domain Burst\n%s - n = %d, %d on / %d off'%(datetime.datetime.utcfromtimestamp(timestamp), cfg['burst_pulses'], sec_on, sec_off))
            plt.show()
            

        elif cfg['TD_FD_SELECT'] == 0:
            # Frequency-domain plotting here:
            fig = plt.figure()
            gs = GridSpec(2, 2, width_ratios=[20, 1])
            E_FD = fig.add_subplot(gs[0,0])
            B_FD = fig.add_subplot(gs[1,0])
            cb1 = fig.add_subplot(gs[0,1])
            cb2 = fig.add_subplot(gs[1,1])

            nfft = 1024
            scale_factor = nfft/2./80000.
            t_axis = np.array([(np.arange(cfg['FFTS_ON'])) +\
                          (k*(cfg['FFTS_ON'] + cfg['FFTS_OFF'])) for k in range(cfg['burst_pulses'])]).ravel()
            t_axis += system_delay_samps_FD        
            t_axis = t_axis*scale_factor 

            print("t axis:", len(t_axis))
            # Frequency axis
            f_axis = []
            seg_length = nfft/2/16
            for i, v in enumerate(cfg['BINS']):
                if v=='1':
                    f_axis.append([np.arange(seg_length)+seg_length*i])

            f_axis = (40000/(nfft/2))*np.array(f_axis).ravel()

            print("f axis:", len(f_axis))
            # print(len(burst['E'])/len(f_axis))
            max_E = len(burst['E']) - np.mod(len(burst['E']), len(f_axis))
            E = burst['E'][0:max_E].reshape(int(max_E/len(f_axis)), len(f_axis))/32768.
            max_B = len(burst['B']) - np.mod(len(burst['B']), len(f_axis))
            B = burst['B'][0:max_E].reshape(int(max_E/len(f_axis)), len(f_axis))/32768.

            
            # clims = [-3, 3]
            clims = [-96, 0];
            Emag = 20*np.log10(np.abs(E.T))
            Emag[np.isinf(Emag)] = -100
            Bmag = 20*np.log10(np.abs(B.T))
            Bmag[np.isinf(Emag)] = -100
            # Spaced
            # pe = E_FD.pcolormesh(t_axis,f_axis/1000, 20*np.log10(np.abs(E.T)), cmap = cm, vmin=clims[0], vmax=clims[1])
            # pb = B_FD.pcolormesh(t_axis,f_axis/1000, 20*np.log10(np.abs(B.T)), cmap = cm, vmin=clims[0], vmax=clims[1])

            # Not spaced
            # pe = E_FD.pcolormesh(Emag, cmap = cm, vmin=clims[0], vmax=clims[1])
            # pb = B_FD.pcolormesh(Bmag, cmap = cm, vmin=clims[0], vmax=clims[1])
            ce = plt.colorbar(pe, cax=cb1)
            cb = plt.colorbar(pb, cax=cb2)

            # E_FD.set_ylim([0, 40])
            # B_FD.set_ylim([0, 40])

        plt.show()
        # fig.savefig(filename, bbox_inches='tight')

if __name__ == '__main__':

    print("plotting burst data...")
    # Load decoded data:
    with open("decoded_data.pkl","rb") as f:
        d = pickle.load(f)

    print(d.keys())

    B_data = d['burst']

    plot_burst_data(B_data, "burst_data.pdf")
