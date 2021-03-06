import numpy as np
import matplotlib.pyplot as plt

import datetime
import matplotlib.gridspec as GS
import matplotlib.dates as mdates
from plots.parula_colormap import parula
import logging
import os
import pickle
from configparser import ConfigParser # for tx map
from file_handlers import load_packets_from_tree, read_burst_XML, read_survey_XML
from matplotlib.cm import get_cmap
from mpl_toolkits.basemap.solar import daynight_terminator
from mpl_toolkits.basemap import Basemap
from scipy.interpolate import interp1d, interp2d
from process_burst_data import save_burst_to_file_tree, gen_burst_plots
from rast_save import rasterize_and_save

def is_day(t, lats, lons):
    # Determine whether or not the satellite is on the dayside.
    # We're using the day-nite terminator function from Basemap.

    tlons, tlats, tau, dec = daynight_terminator(t, 1.1, -180, 180)

    # Lon to lat interpolator
    interpy = interp1d(tlons, tlats,'linear', fill_value='extrapolate')
    thresh_lats = interpy(lons)
    
    if dec > 0: 
        dayvec = lats > thresh_lats
    else:
        dayvec = lats < thresh_lats
        
    return dayvec

def show_transmitters_survey(m, TX_file):
    try:
        call_sign_config = ConfigParser()
        try:
            fp = open(TX_file)
            call_sign_config.read_file(fp)
            fp.close()
        except:
            logger.warning('failed to load transmitters file')

        for tx_name, vals in call_sign_config.items('NB_Transmitters'):
            vv = vals.split(',')
            tx_freq = float(vv[0])
            tx_lat  = float(vv[1])
            tx_lon  = float(vv[2])
            px,py = m(tx_lon, tx_lat)
            p = m.scatter(px,py, marker='p', s=10, color='r',zorder=99)
            #name_str = '{:s}  \n{:0.1f}  '.format(tx_name.upper(), tx_freq/1000)
            #m_ax.text(px, py, name_str, fontsize=8, fontweight='bold', ha='left',
            #    va='bottom', color='k', label='TX')
        p.set_label('TX')
    except:
        logger.warning('Problem plotting narrowband transmitters')

def plot_survey_data_and_metadata(fig, S_data,
                plot_map=True, bus_timestamps=False, t1=15, t2=18,
                line_plots = ['Lshell','altitude','lat','lon','solution_status','daylight'],
                show_plots=True, lshell_file = 'resources/Lshell_dict.pkl', cal_file = None, E_gain=False, B_gain=False):

    if plot_map or (len(line_plots) > 1):
        # The full plot: 
        gs_root = GS.GridSpec(2, 2, height_ratios=[1,2], width_ratios=[1,1.5],  wspace = 0.15, hspace = 0.05, figure=fig)
        gs_data = GS.GridSpecFromSubplotSpec(2, 2, height_ratios=[0.2,10], width_ratios=[20, 0.5], wspace = 0.025, hspace = 0.025, subplot_spec=gs_root[:,1])
        m_ax = fig.add_subplot(gs_root[0,0])
    else:
        gs_data = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, figure = fig)

    # colormap -- parula is a clone of the Matlab colormap; also try plt.cm.jet or plt.cm.viridis
    cm = parula(); #plt.cm.viridis;

    # Sort by header timestamps
    S_data = sorted(S_data, key = lambda f: f['header_timestamp'])

    # Subset of data with GPS stamps included.
    # We need these for the line plots, regardless if we're using payload or bus timestamps.
    # Also confirm that we have at least one field from BESTPOS and BESTVEL messages,
    # since on rare occasions we miss one or the other.
    S_with_GPS = list(filter(lambda x: (('GPS' in x) and 
                                        ('timestamp' in x['GPS'][0]) and
                                        ('lat' in x['GPS'][0]) and
                                        ('horiz_speed' in x['GPS'][0])), S_data))
    S_with_GPS = sorted(S_with_GPS, key = lambda f: f['GPS'][0]['timestamp'])


    T_gps = np.array([x['GPS'][0]['timestamp'] for x in S_with_GPS])
    dts_gps = np.array([datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc) for x in T_gps])

    # Build arrays
    E = []
    B = []
    T = []
    F = np.arange(512)*40/512;
    
    # # Only plot survey data if we have GPS data to match
    if bus_timestamps:

        # Sort using bus timestamp (finer resolution, but 
        # includes transmission error from payload to bus)
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
            gain = S['gain']
            survey_type = S['survey_type']

            if gain == 'high':
                gain_f = 1
            else: # low gain
                gain_f = 10
            if survey_type == 'short':
                shift = 55                                                                                                      
            else: # long survey
                shift = 64
            #print(shift)
            
            # append the calibrated the data
            E.append( (10 * np.log10( gain_f * 2**(S['E_data'] / 8) )) - shift )
            
    T = np.array(T)

    dates = np.array([datetime.datetime.utcfromtimestamp(t) for t in T])

    if t1 is None:
        t1 = dates[0]
    if t2 is None:
        t2 = dates[-1]
    # -----------------------------------
    # Spectrograms
    # -----------------------------------
    E = np.array(E); B = np.array(B); T = np.array(T);


    # gs_data = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, subplot_spec=gs_root[1])
    # ax1 = fig.add_subplot(gs_data[0,0])
    ax2 = fig.add_subplot(gs_data[1,0]) # sharex=ax1, sharey=ax1)
    # e_cbax = fig.add_subplot(gs_data[0,1])
    e_cbax = fig.add_subplot(gs_data[1,1])

    e_clims = [-40,10] #[0,255] #[-80,-40]
    # b_clims = [150,255] #[0,255] #[-80,-40]

    date_edges = np.insert(dates, 0, dates[0] - datetime.timedelta(seconds=26))

    # Insert columns of NaNs wherever we have gaps in data (dt > 27 sec)
    per_sec = 26 # Might want to look this up for the shorter survey modes
    gaps = np.where(np.diff(date_edges) > datetime.timedelta(seconds=(per_sec+2)))[0]

    d_gapped = np.insert(dates, gaps, dates[gaps] - datetime.timedelta(seconds=per_sec + 3))
    E_gapped = np.insert(E.astype('float'), gaps - 1, np.nan*np.ones([1,512]), axis=0)
    B_gapped = np.insert(B.astype('float'), gaps - 1, np.nan*np.ones([1,512]), axis=0)

    # Plot E data
    # p1 = ax1.pcolormesh(d_gapped,F,E_gapped.T, vmin=e_clims[0], vmax=e_clims[1], shading='flat', cmap = cm);
    p2 = ax2.pcolormesh(d_gapped,F,E_gapped.T, vmin=e_clims[0], vmax=e_clims[1], shading='flat', cmap = cm);
    # cb1 = fig.colorbar(p1, cax = e_cbax)
    cb2 = fig.colorbar(p2, cax = e_cbax)
    # cb1.set_label(f'Raw value [{e_clims[0]}-{e_clims[1]}]')
    cb2.set_label('dB[(uV/m)^2/Hz]')

    # # vertical lines at each edge (kinda nice, but messy for big plots)
    # g1 = ax1.vlines(dates, 0, 40, linewidth=0.2, alpha=0.5, color='w')
    # g2 = ax2.vlines(dates, 0, 40, linewidth=0.2, alpha=0.5, color='w')

    ax2.set_xticklabels([])
    # ax1.set_ylim([0,40])
    ax2.set_ylim([0,40])

    formatter = mdates.DateFormatter('%H:%M:%S')
    ax2.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()
    ax2.set_xlabel("Time (H:M:S) on \n%s"%datetime.datetime.utcfromtimestamp(T[0]).strftime("%Y-%m-%d"))
    # ax2.set_xlabel("Time (H:M:S)")

    # ax1.set_ylabel('E channel\nFrequency [kHz]')
    ax2.set_ylabel('E channel Frequency [kHz]')

    # -----------------------------------
    # Ground track Map
    # -----------------------------------

    if plot_map:
        m = Basemap(projection='mill',lon_0=0,ax=m_ax, llcrnrlon=-180,llcrnrlat=-70,urcrnrlon=180,urcrnrlat=70)
        lats = [x['GPS'][0]['lat'] for x in S_with_GPS]
        lons = [x['GPS'][0]['lon'] for x in S_with_GPS]

        sx,sy = m(lons, lats)


        m.drawcoastlines(color='k',linewidth=1,ax=m_ax);
        m.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0]);
        m.drawmeridians(np.arange(m.lonmin,m.lonmax+30,60),labels=[0,0,1,0]);
        m.drawmapboundary(fill_color='cyan');
        m.fillcontinents(color='white',lake_color='cyan');

        TX_file='resources/nb_transmitters.conf'
        show_transmitters_survey(m, TX_file) # add dots for tx

        # This is sloppy -- we need to stash the scatterplot in a persistent object,
        # but because this is just a script and not a class, it vanishes. So we're
        # sticking it into the top figure for now. (This is so we can update the point
        # visibility when zooming in and out in the GUI)
        m_ax.s = m.scatter(sx,sy,c=T_gps, marker='.', s=10, cmap = get_cmap('plasma'), zorder=100, picker=5)
        
        hits = np.where(dates >= datetime.datetime(1979,1,1,0,0,0))

        # Enable click events on the map:
        def onpick(event):
            ''' Event handler for a point click '''
            ind = event.ind
            t_center = dates[ind[0]]

            ax_lines[-1].set_xlim(t_center - datetime.timedelta(minutes=15), t_center + datetime.timedelta(minutes=15))
            onzoom(ax1)
            fig.canvas.draw()


        def onzoom(axis, *args, **kwargs):
            # Update the map to only show points within range:
            [tt1, tt2] = axis.get_xlim()
            d1 = mdates.num2date(tt1)
            d2 = mdates.num2date(tt2)
            hits = np.where((dts_gps >= d1) & (dts_gps <= d2))[0]
            

            try:
                m_ax.s.remove()
            except:
                pass

            m_ax.s = m.scatter(np.array(sx)[hits],np.array(sy)[hits],c=T_gps[hits], marker='.', s=10, cmap = get_cmap('plasma'), zorder=100, picker=5)

        # Attach callback
        # ax1.callbacks.connect('xlim_changed', onzoom)
        ax2.callbacks.connect('xlim_changed', onzoom)

        cid= fig.canvas.mpl_connect('pick_event', lambda event: onpick(event))


    if len(line_plots) > 0:
        gs_lineplots = GS.GridSpecFromSubplotSpec(len(line_plots), 1, hspace=0.5, subplot_spec=gs_root[1,0])

        ax_lines = []

        for ind, a in enumerate(line_plots):
            ax_lines.append(fig.add_subplot(gs_lineplots[ind]))

        markersize = 4
        markerface = '.'
        markeralpha= 0.6
        
        for ind, a in enumerate(line_plots):
            
            if a in S_with_GPS[0]['GPS'][0]:
                yvals = np.array([x['GPS'][0][a] for x in S_with_GPS])
                ax_lines[ind].plot(dts_gps, yvals,markerface, markersize=markersize, label=a, alpha=markeralpha)
                ax_lines[ind].set_ylabel(a, rotation=0, labelpad=30)
            elif a in 'altitude':
                yvals = np.array([x['GPS'][0]['alt'] for x in S_with_GPS])/1000.
                ax_lines[ind].plot(dts_gps, yvals,markerface, markersize=markersize, label=a, alpha=markeralpha)
                ax_lines[ind].set_ylabel('Altitude\n[km]', rotation=0, labelpad=30)
                ax_lines[ind].set_ylim([450,500])
            elif a in 'dt':
                ax_lines[ind].plot(dts_gps, T - T_gps,markerface, markersize=markersize, label=a, alpha=markeralpha)
                ax_lines[ind].set_ylabel(r't$_{header}$ - t$_{GPS}$',  rotation=0, labelpad=30)
            elif a in 'velocity':
                v_horiz = np.array([x['GPS'][0]['horiz_speed'] for x in S_with_GPS])
                v_vert = np.array([x['GPS'][0]['vert_speed'] for x in S_with_GPS])
                vel = np.sqrt(v_horiz*v_horiz + v_vert*v_vert)/1000.

                ax_lines[ind].plot(dts_gps, vel, markerface, markersize=markersize, alpha=markeralpha, label='Velocity')
                ax_lines[ind].set_ylabel('Velocity\n[km/sec]', rotation=0, labelpad=30)
                ax_lines[ind].set_ylim([5,10])
            elif a in 'Lshell':
                try:
                    # This way using a precomputed lookup table:
                    with open(lshell_file,'rb') as file:
                        Ldict = pickle.load(file)
                    L_interp = interp2d(Ldict['glon'], Ldict['glat'], Ldict['L'], kind='cubic')
                    Lshell = np.array([L_interp(x,y) for x,y in zip(lons, lats)])
                    
                    ax_lines[ind].plot(dts_gps, Lshell,markerface, markersize=markersize,  alpha=markeralpha, label='L shell')
                    ax_lines[ind].set_ylabel('L shell', rotation=0, labelpad=30)
                    ax_lines[ind].set_ylim([1,8])
                except:
                    pass
            if a in 'daylight':
                # Day or night based on ground track, using the daynight terminator from Basemap
                dayvec = np.array([is_day(x, y, z) for x,y,z in zip(dts_gps, lats, lons)])
                ax_lines[ind].plot(dts_gps, dayvec, markerface, markersize=markersize,  alpha=markeralpha, label='Day / Night')
                ax_lines[ind].set_yticks([False, True])
                ax_lines[ind].set_yticklabels(['Night','Day'])

        
        fig.autofmt_xdate()


        for a in ax_lines[:-1]:
            a.set_xticklabels([])
            
        # Link line plot x axes:
        for a in ax_lines:
            ax_lines[0].get_shared_x_axes().join(ax_lines[0], a)


        # Link data x axes:
        #ax_lines[0].get_shared_x_axes().join(ax_lines[0], ax1)
        ax_lines[0].get_shared_x_axes().join(ax_lines[0], ax2)

        ax_lines[-1].set_xticklabels(ax_lines[-1].get_xticklabels(), rotation=30)
        ax_lines[-1].xaxis.set_major_formatter(formatter)
        ax_lines[-1].set_xlabel("Time (H:M:S) on \n%s"%datetime.datetime.utcfromtimestamp(T[0]).strftime("%Y-%m-%d"))

        day = datetime.datetime.strptime('VPM_survey_data_2020-06-28.xml', 'VPM_survey_data_%Y-%m-%d.xml')
        d1 = day + datetime.timedelta(hours=15,minutes=0)
        d2 = day + datetime.timedelta(hours=18,minutes=0) 
        ax_lines[-1].set_xlim([d1,d2])
    
    fig.suptitle(f"VPM Survey Data: {day.strftime('%D')}\n" + f"{d1.strftime('%H:%M:%S')} -- {d2.strftime('%H:%M:%S')} UT")
    rasterize_list = [p2]
    rasterize_and_save('/Users/rileyannereid/macworkspace/VPM_data/issues/survey.svg', rasterize_list, dpi=300)

    # -----------------------------------

    return fig


def get_timestamp(x):
    try:
        ts = x['GPS'][0]['timestamp']
    except:
        print("entry is missing GPS data")
        ts = x['header_timestamp']
    return ts

data_root = '/Users/rileyannereid/macworkspace/VPM_data/issues/'
S_data = read_survey_XML(data_root+'VPM_survey_data_2020-06-28.xml')

day = datetime.datetime.strptime('VPM_survey_data_2020-06-28.xml', 'VPM_survey_data_%Y-%m-%d.xml')

d1 = day + datetime.timedelta(hours=15,minutes=0)
d2 = day + datetime.timedelta(hours=18,minutes=0)
t1 = d1.replace(tzinfo = datetime.timezone.utc).timestamp()
t2 = d2.replace(tzinfo = datetime.timezone.utc).timestamp()
S_filt = list(filter(lambda x: (get_timestamp(x) >= t1) and (get_timestamp(x) < t2), S_data))



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
figure = plot_survey_data_and_metadata(fig, S_filt,t1=t1,t2=t2)


burst_file = '/Users/rileyannereid/macworkspace/VPM_data/issues/VPM_burst_TD_2020-06-14_0659.xml'
out_root = '/Users/rileyannereid/macworkspace/VPM_data/issues/'
burst_data = [read_burst_XML(burst_file)]
#gen_burst_plots(burst_data, out_root + '/figures/')