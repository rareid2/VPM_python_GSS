import numpy as np
import matplotlib.pyplot as plt
import pickle
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal
import os
from parula_colormap import parula
import logging


def plot_burst_data(B_data, filename="burst_data.pdf"):

    logger = logging.getLogger(__name__)

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
    for ind, burst in enumerate(B_data):
    # for burst in [B_data[1]]:
        logger.debug(burst['config'])
        cfg = burst['config']
        # if len(burst['G']) > 0:
        #     timestamp = burst['G'][0]['timestamp']  # This might be a list of timestamps for windowed bursts
        #     for g in burst['G']:
        #         logger.info(f"GPS timestamp: {datetime.datetime.utcfromtimestamp(g['timestamp'])}")
        # else:
        #     timestamp = 0 #datetime.datetime(1970,1,1,0,0,0).timestamp()

        logger.info(f'burst configuration: {cfg}')



        system_delay_samps_TD = 73;    
        system_delay_samps_FD = 200;
        fs = 80000;
        # cm = plt.cm.jet
        cm = parula();


        if cfg['TD_FD_SELECT'] == 1:
            # Time domain mode
            fig = plt.figure()
            gs = GridSpec(2, 3, width_ratios=[20, 20, 1])
            E_TD = fig.add_subplot(gs[0,0])
            B_TD = fig.add_subplot(gs[1,0], sharex=E_TD)
            E_FD = fig.add_subplot(gs[0,1], sharex=E_TD)
            B_FD = fig.add_subplot(gs[1,1], sharex=E_FD)
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

            # Get the timestamp at the beginning of the burst.
            # GPS timestamps are taken at the end of each contiguous recording.
            # (I think "samples on" is still undecimated, regardless if decimation is being used...)
            start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=float(cfg['SAMPLES_ON']/fs))

            # the "samples on" and "samples off" values are counting at the full rate, not the decimated rate.
            sec_on  = cfg['SAMPLES_ON']/fs
            sec_off = cfg['SAMPLES_OFF']/fs
            
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
            ff,tt, FE = scipy.signal.spectrogram(E_td_spaced/32768., fs=fs_equiv, window=window,
                        nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density')
            E_S_mag = 20*np.log10(np.sqrt(FE))
            E_S_mag[np.isinf(E_S_mag)] = -100
            logger.debug(f'E data min/max: {np.min(E_S_mag)}, {np.max(E_S_mag)}')
        #     pe = E_FD.pcolormesh(tt,ff,np.log10(E_S_mag), cmap = cm, shading='gouraud')
            pe = E_FD.pcolorfast(tt,ff/1000,E_S_mag, cmap = cm,  vmin=clims[0], vmax=clims[1])
            ce = plt.colorbar(pe, cax=cb1)

            # B spectrogram
            ff,tt, FB = scipy.signal.spectrogram(B_td_spaced/32768., fs=fs_equiv, window=window,
                        nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density')
            B_S_mag = 20*np.log10(np.sqrt(FB))
            B_S_mag[np.isinf(B_S_mag)] = -100
            logger.debug(f'B data min/max: {np.min(B_S_mag)}, {np.max(B_S_mag)}')
        #     pb = B_FD.pcolormesh(tt,ff, np.log10(B_S_mag), cmap = cm, shading='gouraud')
            pb = B_FD.pcolorfast(tt,ff/1000, B_S_mag, cmap = cm,  vmin=clims[0], vmax=clims[1])
            cb = plt.colorbar(pb, cax=cb2)

            # E_TD.set_xticklabels([])
            # E_FD.set_xticklabels([])

            E_TD.set_ylabel('E\nAmplitude')
            B_TD.set_ylabel('B\nAmplitude')
            E_FD.set_ylabel('Frequency [kHz]')
            B_FD.set_ylabel('Frequency [kHz]')
            B_TD.set_xlabel('Time [sec from start]')
            B_FD.set_xlabel('Time [sec from start]')

            ce.set_label('dB(sqrt(psd))')
            cb.set_label('dB(sqrt(psd))')

            fig.suptitle('Time-Domain Burst\n%s - n = %d, %d on / %d off'%(start_timestamp, cfg['burst_pulses'], sec_on, sec_off))
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

            # Frequency axis
            f_axis = []
            seg_length = nfft/2/16

            for i, v in enumerate(np.flip(cfg['BINS'])):
                if v=='1':
                    f_axis.append([np.arange(seg_length)+seg_length*i])

            f_axis = (40000/(nfft/2))*np.array(f_axis).ravel()

            logger.debug(f"f axis: {len(f_axis)}")
            
            # E and B are flattened vectors; we need to reshape them into 2d arrays (spectrograms)
            max_E = len(burst['E']) - np.mod(len(burst['E']), len(f_axis))
            E = burst['E'][0:max_E].reshape(int(max_E/len(f_axis)), len(f_axis))/32768.
            max_B = len(burst['B']) - np.mod(len(burst['B']), len(f_axis))
            B = burst['B'][0:max_B].reshape(int(max_B/len(f_axis)), len(f_axis))/32768.
            
            logger.debug(f"E dims: {np.shape(E)}, B dims: {np.shape(B)}")

            scale_factor = nfft/2./80000.
            if cfg['FFTS_OFF'] == 0:
                # probably don't have burst_pulses decoded correctly, since we're just counting received GPS
                # packets. GPS packets are taken when stopping data capture -- e.g., at the end of the burst,
                # or transitioning to a "samples off" section.
                t_axis = np.arange(np.shape(E)[0])*scale_factor
                start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=np.round(t_axis[-1]))
            else:
                t_axis = np.array([(np.arange(cfg['FFTS_ON'])) +\
                              (k*(cfg['FFTS_ON'] + cfg['FFTS_OFF'])) for k in range(cfg['burst_pulses'])]).ravel()
                t_axis += system_delay_samps_FD        
                t_axis = t_axis*scale_factor     
                start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=np.round(cfg['FFTS_ON']*scale_factor))

            clims = [-96, 0];
            Emag = 20*np.log10(np.abs(E.T))
            Emag[np.isinf(Emag)] = -100
            Bmag = 20*np.log10(np.abs(B.T))
            Bmag[np.isinf(Bmag)] = -100
            # Spaced
            
            
            # pe = E_FD.pcolormesh(t_axis,f_axis/1000, 20*np.log10(np.abs(E.T)), cmap = cm, vmin=clims[0], vmax=clims[1])
            # pb = B_FD.pcolormesh(t_axis,f_axis/1000, 20*np.log10(np.abs(B.T)), cmap = cm, vmin=clims[0], vmax=clims[1])

            # Not spaced
            pe = E_FD.pcolormesh(Emag, cmap = cm, vmin=clims[0], vmax=clims[1])
            pb = B_FD.pcolormesh(Bmag, cmap = cm, vmin=clims[0], vmax=clims[1])
            ce = plt.colorbar(pe, cax=cb1)
            cb = plt.colorbar(pb, cax=cb2)

            E_FD.set_ylim([0, 40])
            B_FD.set_ylim([0, 40])

            B_FD.set_xlabel('Time [sec from start]')
        fig.suptitle(f'Burst {ind}\n{start_timestamp}')    
        plt.show()
        # fig.savefig(filename, bbox_inches='tight')


        # Save it!
        if ind == 0:
            fname = filename
        else:
            components = os.path.splitext(filename)
            fname = components[0] + f"_{ind}" + components[1]

        # fig.savefig(fname, bbox_inches='tight')

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    print("plotting burst data...")
    # Load decoded data:
    # with open("decoded_data.pkl","rb") as f:
    with open("output/decoded_data.pkl","rb") as f:
        d = pickle.load(f)

    print(d.keys())

    B_data = d['burst']

    plot_burst_data(B_data, "burst_data.pdf")
