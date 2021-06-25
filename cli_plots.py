# This module exists as an interface to the "plots" methods.
# We have this here so that the plots themselves can be used fo the GUI and 
# the CLI versions; but figure setup is different enough that they're
# not directly compatible (Also TKinter crashes if you import pyplot).

import matplotlib.pyplot as plt
import logging
import os
import pickle

from plots.plot_survey_data_and_metadata import plot_survey_data_and_metadata as plot_survey_core
from plots.plot_burst_data import plot_burst_TD, plot_burst_FD
#from plots.plot_incomplete_burst import plot_burst_incomplete
from plots.plot_burst_map import plot_burst_map as plot_map

def plot_survey_data_and_metadata(S_data, **kwargs):

    # Set up the frame:
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 12
    fig_height = 8
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 8,
              'font.size': 10,
              'legend.fontsize': 8,
              'xtick.labelsize': 8,
              'ytick.labelsize': 8,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------

    fig = plt.figure()

    # Call the core function
    plot_survey_core(fig, S_data, **kwargs)

    return fig


def plot_burst_data(B_data, filename="burst_data.png", show_plots=False, 
    cal_file=None, dpi=150, **kwargs):

    logger = logging.getLogger('plot_burst_data')
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 12 
    fig_height = 8
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------

    # Cal data?
    cal_data = None
    if cal_file:    
        try:
            with open(cal_file,'rb') as file:
                logger.info(f'loading calibration file {cal_file}')
                cal_data = pickle.load(file)
        except:
            logger.warning(f'Failed to load calibration file {cal_file}')
        

    for ind, burst in enumerate(B_data):
        logger.info(f'plotting burst {ind}')
        cfg = burst['config']
        fig = plt.figure()

        if cfg['TD_FD_SELECT'] == 1:
            plot_burst_TD(fig, burst, cal_data = cal_data)

        elif cfg['TD_FD_SELECT'] == 0:
            plot_burst_FD(fig, burst, cal_data = cal_data)

        # Show it?
        if show_plots:
            plt.show()

        # Save it!
        if ind == 0:
            fname = filename
        else:
            components = os.path.splitext(filename)
            fname = components[0] + f"_{ind}" + components[1]

        if filename:
            fig.savefig(filename, bbox_inches='tight', dpi=dpi)


def plot_burst_inc(B_data, filename="burst_data.png", show_plots=False, 
    cal_file=None, dpi=150, **kwargs):

    logger = logging.getLogger('plot_burst_data')
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 12 
    fig_height = 8
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------

    # Cal data?
    cal_data = None
    if cal_file:    
        try:
            with open(cal_file,'rb') as file:
                logger.info(f'loading calibration file {cal_file}')
                cal_data = pickle.load(file)
        except:
            logger.warning(f'Failed to load calibration file {cal_file}')
        

    for ind, burst in enumerate(B_data):
        logger.info(f'plotting burst {ind}')
        cfg = burst['config']
        fig = plt.figure()

        if cfg['TD_FD_SELECT'] == 1:
            plot_burst_incomplete(fig, burst, cal_data = cal_data)

        elif cfg['TD_FD_SELECT'] == 0:
            plot_burst_FD(fig, burst, cal_data = cal_data)

        # Show it?
        if show_plots:
            plt.show()

        # Save it!
        if ind == 0:
            fname = filename
        else:
            components = os.path.splitext(filename)
            fname = components[0] + f"_{ind}" + components[1]

        if filename:
            fig.savefig(filename, bbox_inches='tight', dpi=dpi)

def plot_burst_map(B_data, filename="burst_map.png", show_plots = False, dpi=150,
                **kwargs):
    
    logger = logging.getLogger('plot_burst_map')
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 12 
    fig_height = 7
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------


    for ind, burst in enumerate(B_data):
        logger.info(f'plotting burst {ind}')
        cfg = burst['config']
        fig = plt.figure()
    
        if len(burst['G']) > 0:
            plot_map(fig, burst['G'], **kwargs)        

            # Show it?
            if show_plots:
                plt.show()

            # Save it!
            if ind == 0:
                fname = filename
            else:
                components = os.path.splitext(filename)
                fname = components[0] + f"_{ind}" + components[1]

            if filename:
                fig.savefig(filename, bbox_inches='tight', dpi=dpi)

