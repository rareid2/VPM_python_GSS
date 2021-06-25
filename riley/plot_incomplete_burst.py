import numpy as np
# import matplotlib.pyplot as plt
import pickle
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal
import os
from plots.parula_colormap import parula
import logging
import argparse
from file_handlers import read_burst_XML
from data_handlers import decode_status
from data_handlers import decode_uBBR_command
import pickle

from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
from plots.plot_burst_map import plot_burst_map

# updated to no longer plot B-field data and add 
# map to same figure

def plot_burst_incomplete(fig, burst, cal_data = None):
    
    logger = logging.getLogger("plot_burst_TD")

    cfg = burst['config']

    logger.info(f'burst configuration: {cfg}')

    system_delay_samps_TD = 73;    
    system_delay_samps_FD = 200;
    fs = 80000;
    # cm = plt.cm.jet
    cm = parula();  # This is a mockup of the current Matlab colormap (which is proprietary)


    # Check if we have any status packets included -- we'll get
    # the uBBR configuration from these.
    if 'bbr_config' in burst:
        bbr_config =burst['bbr_config']
    elif 'I' in burst:
        logger.debug(f"Found {len(burst['I'])} status packets")
            # Get uBBR config command:
        if 'prev_bbr_command' in burst['I'][0]:
            bbr_config = decode_uBBR_command(burst['I'][0]['prev_bbr_command'])
        else:
            ps = decode_status([burst['I'][0]])
            bbr_config = decode_uBBR_command(ps[0]['prev_bbr_command'])
        logger.debug(f'bbr config is: {bbr_config}')
    else:
        logger.warning(f'No bbr configuration found')
        bbr_config = None

    E_unit_string = 'uV/m' # now calibrated to uV/m

    # Scale the spectrograms -- A perfect sine wave will have ~-3dB amplitude.
    # Scaling covers 14 bits of dynamic range, with a maximum at each channel's theoretical peak
    #clims = np.array([-6*14, -3]) #[-96, -20]
    #e_clims = clims + 20*np.log10(E_coef*ADC_max_value/ADC_max_volts)
    #b_clims = clims + 20*np.log10(B_coef*ADC_max_value/ADC_max_volts)
    
    e_clims = np.array([-40, 10]) # for newly calibrated data

    E_coef = burst['CAL'] # calibrate into uV/m units 
    #print(E_coef)
    B_coef = 1 # just so we don't have to comment a bunch of stuff out
    
    # Generate time axis
    if cfg['TD_FD_SELECT'] == 1:
# --------- Time domain plots  -----------
        # fig = plt.figure()
        fig.set_size_inches(10,8)
        gs = GridSpec(2, 2, height_ratios=[1.25,1], wspace = 0.2, hspace = 0.25)
        E_TD = fig.add_subplot(gs[0,0])
        # B_TD = fig.add_subplot(gs[1,0], sharex=E_TD)
        E_FD = fig.add_subplot(gs[0,1], sharex=E_TD)
        # B_FD = fig.add_subplot(gs[1,1], sharex=E_FD)
        # cb1  = fig.add_subplot(gs[0,2])
        # cb2  = fig.add_subplot(gs[1,2])

        # add in burst map to plot -- werid workaround but it fixed it
        map_ax = fig.add_subplot(gs[1,0:2])
        box = map_ax.get_position()
        box.x0 = box.x0 - 0.13
        box.x1 = box.x1 - 0.13
        map_ax.set_position(box)
        gstr = plot_burst_map(map_ax, burst['G'], burst)
    
        fig.text(0.68, 0.25, gstr, fontsize='9') # ha='center', va='bottom')

        # Construct the appropriate time and frequency axes
        # Get the equivalent sample rate, if decimated
        if cfg['DECIMATE_ON']==1:
            fs_equiv = 80000./cfg['DECIMATION_FACTOR']
        else:
            fs_equiv = 80000.

        if cfg['SAMPLES_OFF'] == 0:
            max_ind = max(len(burst['E']), len(burst['B']))
            t_axis = np.arange(max_ind)/fs_equiv
        else:

            # Seconds from the start of the burst
            t_axis = np.array([(np.arange(cfg['SAMPLES_ON']))/fs_equiv +\
                          (k*(cfg['SAMPLES_ON'] + cfg['SAMPLES_OFF']))/fs_equiv for k in range(cfg['burst_pulses'])]).ravel()
        #print(len(burst['E']))

        # Add in system delay 
        t_axis += system_delay_samps_TD/fs_equiv 

        # Get the timestamp at the beginning of the burst.
        # GPS timestamps are taken at the end of each contiguous recording.
        # (I think "samples on" is still undecimated, regardless if decimation is being used...)
        try:
            start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=float(cfg['SAMPLES_ON']/fs))
            #print(start_timestamp)
        except:
            start_timestamp = datetime.datetime.utcfromtimestamp(burst['header_timestamp'])

        #if start_timestamp.year == 1980:
        #    # error in GPS? 
        #    start_timestamp = datetime.datetime.utcfromtimestamp(burst['header_timestamp'])

        # the "samples on" and "samples off" values are counting at the full rate, not the decimated rate.
        sec_on  = cfg['SAMPLES_ON']/fs
        sec_off = cfg['SAMPLES_OFF']/fs
        

        #E_TD.plot(t_axis[0:len(burst['E'])], E_coef*burst['E'])
        E_TD.plot(t_axis[0:len(burst['E'])], E_coef*burst['E'][0:len(t_axis)])
        # B_TD.plot(t_axis[0:len(burst['B'])], B_coef*burst['B'])


        # E_TD.set_ylim(td_lims)
        # B_TD.set_ylim(td_lims)

        nfft=1024;
        overlap = 0.5
        window = 'hanning'

        
        if cfg['SAMPLES_OFF'] == 0:
            E_td_spaced = E_coef*burst['E']
            B_td_spaced = B_coef*burst['B']
        else:
            # Insert nans into vector to account for "off" time sections
            E_td_spaced = []
            B_td_spaced = []
            
            for k in np.arange(cfg['burst_pulses']):
                E_td_spaced.append(E_coef*burst['E'][k*cfg['SAMPLES_ON']:(k+1)*cfg['SAMPLES_ON']])
                E_td_spaced.append(np.ones(cfg['SAMPLES_OFF'])*np.nan)
                B_td_spaced.append(B_coef*burst['B'][k*cfg['SAMPLES_ON']:(k+1)*cfg['SAMPLES_ON']])
                B_td_spaced.append(np.ones(cfg['SAMPLES_OFF'])*np.nan)


            E_td_spaced = np.concatenate(E_td_spaced).ravel()
            B_td_spaced = np.concatenate(B_td_spaced).ravel()


        # E spectrogram -- "spectrum" scaling -> V^2; "density" scaling -> V^2/Hz
        ff,tt, FE = scipy.signal.spectrogram(E_td_spaced, fs=fs_equiv, window=window,
                    nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='density') # changed to density
        E_S_mag = 20*np.log10(np.sqrt(FE))
        E_S_mag[np.isinf(E_S_mag)] = -100
        
        logger.debug(f'E data min/max: {np.min(E_S_mag)}, {np.max(E_S_mag)}')

        E_FD.plot(ff/1000, E_S_mag)
        # what does pe do? 
        #pe = E_FD.pcolorfast(tt,ff/1000,E_S_mag, cmap = cm,  vmin=e_clims[0], vmax=e_clims[1])
        #cax_divider = make_axes_locatable(E_FD)
        #ce_ax = cax_divider.append_axes('right', size='7%', pad='5%')
        #ce = fig.colorbar(pe, cax=ce_ax)

        E_TD.set_ylabel(f'E Amplitude\n[{E_unit_string}]')
        E_FD.set_ylabel(f'E Amplitude\n[{E_unit_string}]')
        E_TD.set_xlabel('Time [sec from start]')
        E_FD.set_xlabel('Frequency [kHz]')

        #ce.set_label(f'dB[(uV/m)^2/Hz]')

        #f start_timestamp.year == 1980:
        #        start_timestamp = datetime.datetime.utcfromtimestamp(burst['header_timestamp'])
        start_timestamp = start_timestamp.replace(microsecond=0)
        if bbr_config:
            fig.suptitle('VPM Burst Data\n%s - n = %d, %d on / %d off\nE gain = %s, E filter = %s'
                %(start_timestamp, cfg['burst_pulses'], sec_on, sec_off, burst['GAIN'], burst['FILT']))
        else:
            fig.suptitle('VPM Burst Data\n%s - n = %d, %d on / %d off'
                %(start_timestamp, cfg['burst_pulses'], sec_on, sec_off))
        #fig.savefig(filename, bbox_inches='tight')