import numpy as np
import matplotlib.pyplot as plt
import pickle
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal


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

        cfg = burst['config']
        timestamp = burst['G']['time']  # This might be a list of timestamps for windowed bursts

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

            td_lims = [-1,1]
            E_TD.plot(burst['t_axis'], burst['E'])
            B_TD.plot(burst['t_axis'], burst['B'])
            E_TD.set_ylim(td_lims)
            B_TD.set_ylim(td_lims)

            fs = 80000;
            nfft=1024;
            overlap = 0.5
            window = 'hanning'
            cm = plt.cm.viridis


            # E spectrogram
            ff,tt, FE = scipy.signal.spectrogram(burst['E'], fs=fs, window=window,
                        nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density')
            E_S_mag = np.sqrt(FE)
            print(np.min(E_S_mag), np.max(E_S_mag))
        #     pe = E_FD.pcolormesh(tt,ff,np.log10(E_S_mag), cmap = cm, shading='gouraud')
            pe = E_FD.pcolorfast(tt,ff/1000,np.log10(E_S_mag), cmap = cm)
            ce = plt.colorbar(pe, cax=cb1)

            # B spectrogram
            ff,tt, FB = scipy.signal.spectrogram(burst['B'], fs=fs, window=window,
                        nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density')
            B_S_mag = np.sqrt(FB)
            print(np.min(B_S_mag), np.max(B_S_mag))
        #     pb = B_FD.pcolormesh(tt,ff, np.log10(B_S_mag), cmap = cm, shading='gouraud')
            pb = B_FD.pcolorfast(tt,ff/1000, np.log10(B_S_mag), cmap = cm)
            cb = plt.colorbar(pb, cax=cb2)

            E_TD.set_xticklabels([])
            E_FD.set_xticklabels([])

            E_TD.set_ylabel('E\nAmplitude')
            B_TD.set_ylabel('B\nAmplitude')
            E_FD.set_ylabel('Frequency [kHz]')
            B_FD.set_ylabel('Frequency [kHz]')
            B_TD.set_xlabel('Time [sec]')
            B_FD.set_xlabel('Time [sec]')

            fig.suptitle('Time-Domain Burst\n%s'%timestamp)
            

        elif cfg['TD_FD_SELECT'] == 0:
            # to do: implement frequency-domain plotting here
            pass
            


        # plt.show()
        fig.savefig(filename, bbox_inches='tight')

if __name__ == '__main__':

    print("plotting burst data...")
    # Load decoded data:
    with open("decoded_data.pkl","rb") as f:
        d = pickle.load(f)
    print(d.keys())

    B_data = d['burst']

    plot_burst_data(B_data, "burst_data.pdf")
