from mpl_toolkits.basemap import Basemap
import numpy as np
import datetime
import logging
from compute_ground_track import compute_ground_track
from matplotlib.cm import get_cmap
from configparser import ConfigParser

def plot_burst_map(sub_axis, gps_data, 
        show_terminator = True, plot_trajectory=True, show_transmitters=True,
        TLE_file = None, TX_file='resources/nb_transmitters.conf'):

    logger = logging.getLogger()

    #m_ax = fig.add_subplot(1,1,1)
    m_ax = sub_axis

    m = Basemap(projection='mill',lon_0=0,ax=m_ax, llcrnrlon=-180,llcrnrlat=-70,urcrnrlon=180,urcrnrlat=70)

    lats = [x['lat'] for x in gps_data]
    lons = [x['lon'] for x in gps_data]
    T_gps = np.array([x['timestamp'] for x in gps_data])

    sx,sy = m(lons, lats)

    m.drawcoastlines(color='k',linewidth=1,ax=m_ax);
    m.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0]);
    m.drawmeridians(np.arange(m.lonmin,m.lonmax+30,60),labels=[0,0,1,0]);
    m.drawmapboundary(fill_color='cyan');
    m.fillcontinents(color='white',lake_color='cyan');

    if show_terminator:
        try:
            # Find the median timestamp to use:
            avg_ts = np.mean([k['timestamp'] for k in gps_data if k['time_status'] > 20])

            CS=m.nightshade(datetime.datetime.utcfromtimestamp(avg_ts))
        except:
            logger.warning('Problem plotting day/night terminator')

    if plot_trajectory:
        try:
            if TLE_file:
                try:
                    with open(TLE_file,'r') as file:
                        TLE = file.read().split('\n')
                        logger.info(
                            f'loaded TLE file {TLE_file}')
                except:
                    logger.warning(f'failed to load TLE file {TLE_file}')
            else:
                logger.info('using default TLE')
                # A default TLE, from mid-may 2020.
                TLE = ["1 45120U 19071K   20153.15274580 +.00003602 +00000-0 +11934-3 0  9995",
                       "2 45120 051.6427 081.8638 0012101 357.8092 002.2835 15.33909680018511"]

            avg_ts = np.mean([k['timestamp'] for k in gps_data if k['time_status'] > 20])
            t_mid = datetime.datetime.utcfromtimestamp(avg_ts)
            t1 = t_mid - datetime.timedelta(minutes=15)
            t2 = t_mid + datetime.timedelta(minutes=15)

            traj, tvec = compute_ground_track(TLE, t1, t2, tstep=datetime.timedelta(seconds=10))

            tlats = traj[:,1]
            tlons = traj[:,0]
            simtime = [x.replace(tzinfo=datetime.timezone.utc).timestamp() for x in tvec]

            mid_ind = np.argmin(np.abs(np.array(tvec) - t_mid))
            zx,zy = m(tlons, tlats)
            z = m.scatter(zx,zy,c=simtime, marker='.', s=10, alpha=0.5, cmap = get_cmap('plasma'), zorder=100, label='TLE')

            z2 =m.scatter(zx[mid_ind], zy[mid_ind],edgecolor='k', marker='*',s=50, zorder=101, label='Center (TLE)')
        except:
            logger.warning('Problem plotting ground track from TLE')

    if show_transmitters:
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
                p = m.scatter(px,py, marker='p', s=20, color='r',zorder=99)
                name_str = '{:s}  \n{:0.1f}  '.format(tx_name.upper(), tx_freq/1000)
                m_ax.text(px, py, name_str, fontsize=8, fontweight='bold', ha='left',
                    va='bottom', color='k', label='TX')
            p.set_label('TX')
            s = m.scatter(sx,sy,c=T_gps, marker='o', s=20, cmap = get_cmap('plasma'), zorder=100, label='GPS')
        except:
            logger.warning('Problem plotting narrowband transmitters')
    m_ax.legend(bbox_to_anchor=(1.05,1), loc='upper left', ncol=2)

    gstr = ''
    for entry in gps_data:
        time = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(entry['timestamp']),'%D %H:%M:%S')
        tloc = entry['time_status'] > 20
        ploc = entry['solution_status'] ==0
        gstr+= '{:s} ({:1.2f}, {:1.2f}):\ntime lock: {:b} position lock: {:b}\n'.format(time, entry['lat'], entry['lon'], tloc,ploc)

    # m_ax.text(1, 0, gstr, fontsize='10') # ha='center', va='bottom')
    return gstr
