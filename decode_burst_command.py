import numpy as np
import logging

def decode_burst_command(cmd):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Parses a three-byte command sequence from VPM; returns a dictionary
        stocked with various configuration parameters describing the burst.

    outputs:
        A dictionary containing:
            TD_FD_SELECT: 1 for time domain, 0 for frequency domain
            
            If time domain is selected:
                WINDOWING: 1 for time-axis windowing; 0 for just taking straight data
                WINDOW_MODE: configuration parameter describing the on/off duty cycle
                DECIMATE_ON: 1 to decimate data, 0 to record full 80kHz
                DECIMATION_MODE: A setting describing the downsampling factor
                DECIMATION_FACTOR: The decimation factor, e.g., downsample by 2, 4, 8, or 16x.
                SAMPLES_ON, SAMPLES_OFF: The number of samples to collect and to wait
            
            If frequency domain is selected:
                FFTS_ON, FFTS_OFF: The number of FFT columns to collect and to wait
                BINS: A string of 16 ones or zeros, corresponding to 16, uniformly-divided
                      bins along the frequency axis (nominally 512 bins, spanning 0 to 40 kHz).
                      A '1' enables data collection for this bin.
    '''
    logger = logging.getLogger(__name__)

    logger.debug(f'decoding command: {cmd}')
    cmd_str = ''.join("{0:8b}".format(x) for x in cmd).replace(' ','0')
    
    if not cmd_str[0:2]=='01':
        logger.warning(f'invalid DPU command: {cmd}')

    burst_cmd = dict()
    burst_cmd['str'] = cmd_str
    burst_cmd['TD_FD_SELECT'] = int(cmd_str[2])
    burst_cmd['WINDOWING'] = int(cmd_str[3])
    burst_cmd['WINDOW_MODE'] = int(cmd_str[4:8],2)
    burst_cmd['DECIMATE_ON'] = int(cmd_str[8])
    burst_cmd['DECIMATION_MODE'] = int(cmd_str[9:11],2)
    burst_cmd['BINS'] = cmd_str[8:24];


    # Generate derived parameters:
    # Table of samples on and off, for time and frequency domain
    td_samples_on_vec  = np.array([10, 10, 10, 10,  5,  5, 5, 5,  2,  2, 2, 2,  1,  1, 1, 1])*80000;
    td_samples_off_vec = np.array([30, 10,  5,  2, 30, 10, 5, 2, 30, 10, 5, 2, 30, 10, 5, 2])*80000;
    fd_samples_on_vec  = np.array([1563, 1563, 1563, 1563,  782,  782, 782, 782,  313,  313, 313, 313,  157,  157, 157, 157])
    fd_samples_off_vec = np.array([4688, 1563,  782,  313, 4688, 1563, 782, 313, 4688, 1563, 782, 313, 4688, 1563, 782, 313]) 
    decimation_factors = np.array([2, 4, 8, 16])

    if burst_cmd['TD_FD_SELECT']==1:
        # Time-domain burst
        if burst_cmd['WINDOWING'] == 1:
            burst_cmd['SAMPLES_ON']  = td_samples_on_vec[burst_cmd['WINDOW_MODE']]
            burst_cmd['SAMPLES_OFF'] = td_samples_off_vec[burst_cmd['WINDOW_MODE']]
        else:
            burst_cmd['SAMPLES_ON'] = 30*80000;
            burst_cmd['SAMPLES_OFF'] = 0;

        if burst_cmd['DECIMATE_ON'] ==1:
            burst_cmd['DECIMATION_FACTOR'] = decimation_factors[burst_cmd['DECIMATION_MODE']]

    if burst_cmd['TD_FD_SELECT'] ==0:
        # Frequency-domain burst
        if burst_cmd['WINDOWING'] == 1:
            burst_cmd['FFTS_ON']  = fd_samples_on_vec[burst_cmd['WINDOW_MODE']]
            burst_cmd['FFTS_OFF'] = fd_samples_off_vec[burst_cmd['WINDOW_MODE']]
        else:
            burst_cmd['FFTS_ON'] = 4688;
            burst_cmd['FFTS_OFF']= 0;

    return burst_cmd;
