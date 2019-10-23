import netCDF4

    
def write_survey_netCDF(data, filename='survey_data.nc'):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.19.2019
    Description:
        Writes decoded survey data to a netCDF file

    inputs: 
        data: A list of dictionaries, as generated from decode_survey_data.py
        filename: The output file; please use a ".nc" suffix
    outputs:
        A saved file at <filename>
    '''


    f = netCDF4.Dataset(filename,"w")
    time = f.createDimension("time",None)
    freq = f.createDimension("frequency",512)

    E = f.createVariable('data/E','uint8',('time','frequency'))
    E.description = "Electric field survey data"

    B = f.createVariable('data/B','uint8',('time','frequency'))
    B.description = "Magnetic field survey data"

    T = f.createVariable('data/T','i4',('time'))
    T.description = "time (UNIX timestamp, UTC)"

    lat = f.createVariable('GPS/lat','d',('time'))
    lat.description = "geo latitude"
    lat.units = 'deg'
    lon = f.createVariable('GPS/lon','d',('time'))
    lon.description = "geo longitude"
    lon.units = 'deg'
    alt = f.createVariable('GPS/alt','d',('time'))
    alt.description = 'height above sea level'
    alt.units = 'm'
    v_horiz = f.createVariable('GPS/vel_horiz','d',('time'))
    v_horiz.description="Horizontal velocity"
    v_horiz.units="m/s"
    v_vert = f.createVariable('GPS/vel_vert','d',('time'))
    v_vert.description="Vertical velocity"
    v_vert.units='m/s'
    v_gt = f.createVariable('GPS/ground_track','d',('time'))
    v_gt.description="Ground track direction"
    v_gt.units='deg'

    # GPS metadata:
    tracked_sats = f.createVariable('GPS/metadata/tracked_sats','I',('time'))
    used_sats    = f.createVariable('GPS/metadata/used_sats','I',('time'))
    soln_status  = f.createVariable('GPS/metadata/solution_status','I',('time'))
    soln_type    = f.createVariable('GPS/metadata/solution_type','I',('time'))
    latency      = f.createVariable('GPS/metadata/latency','f4',('time'))

    # Flip through the list, sorted by timestamp
    for i, d in enumerate(sorted(outs['survey'], key = lambda i: i['GPS']['timestamp'])):
        E[i,:] = d['E_data']
        B[i,:] = d['B_data']

        T[i] = d['GPS']['timestamp']

        lat[i] = d['GPS']['lat']
        lon[i] = d['GPS']['lon']
        alt[i] = d['GPS']['alt']
        
        v_horiz[i] = d['GPS']['horiz_speed']
        v_vert[i]  = d['GPS']['vert_speed']
        v_gt[i]    = d['GPS']['ground_track']

        # GPS metadata
        tracked_sats[i] = d['GPS']['tracked_sats']
        used_sats[i]    = d['GPS']['used_sats']
        soln_status[i]  = d['GPS']['solution_status']
        soln_type[i]    = d['GPS']['solution_type']
        latency[i].     = d['GPS']['latency']

    f.close()


def write_burst_netCDF(data, filename='burst_data.nc'):

    datatype = 'f4' # single, double? int? The original data is 16 bit

    f = netCDF4.Dataset(filename,"w")

    # Burst configuration parameters:
    cfg = f.createGroup('config')
    for k,v in data['config'].items():
        setattr(cfg, k, v)

    time = f.createDimension("time",None)

    # There's a timestamp corresponding to each nPulses; each timestamp object is a position and velocity message.
    # TODO: have decode_GPS return a list of timestamps
    ts = f.createDimension("timestamps",None) 
    f_gps = f.createGroup('GPS')

    if data['config']['TD_FD_SELECT'] ==1:
        # Time-domain mode:


        E = f.createVariable('data/E',datatype,('time'))
        E.description = "Electric field burst data"
        E.units = "eng. units"
        E[:] = data['E']

        B = f.createVariable('data/B',datatype,('time'))
        B.description = "Magnetic field burst data"
        B.units = "eng. units"
        B[:] = data['B']
        
        T = f.createVariable('data/t_axis',datatype,('time'))
        T.description = "time axis (seconds elapsed from beginning of burst)"
        T[:] = data['t_axis']

    else:
        # Frequency-domain mode:
        
        freq = f.createDimension("frequency",len(data['f_axis']))
        
        E = f.createVariable('data/E',datatype,('time','freq'))
        E.description = "Electric field survey data"
        E[:] = data['E']

        B = f.createVariable('data/B',datatype,('time','freq'))
        B.description = "Magnetic field burst data"
        B[:] = data['B']

        T = f.createVariable('data/t_axis',datatype,('time'))
        T.description = "time axis (seconds elapsed from beginning of burst)"
        T[:] = data['t_axis']
        
        F = f.createVariable('data/f_axis',datatype,('freq'))
        F.description = "frequency"
        f.units = 'Hz'
        F[:] = data['f_axis']

    # GPS data:
    lat = f.createVariable('GPS/lat','d',('timestamps'))
    lat.description = "geo latitude"
    lat.units = 'deg'
    lon = f.createVariable('GPS/lon','d',('timestamps'))
    lon.description = "geo longitude"
    lon.units = 'deg'
    alt = f.createVariable('GPS/alt','d',('timestamps'))
    alt.description = 'height above sea level'
    alt.units = 'm'
    v_horiz = f.createVariable('GPS/vel_horiz','d',('timestamps'))
    v_horiz.description="Horizontal velocity"
    v_horiz.units="m/s"
    v_vert = f.createVariable('GPS/vel_vert','d',('timestamps'))
    v_vert.description="Vertical velocity"
    v_vert.units='m/s'
    v_gt = f.createVariable('GPS/ground_track','d',('timestamps'))
    v_gt.description="Ground track direction"
    v_gt.units='deg'

    # GPS metadata:
    tracked_sats = f.createVariable('GPS/metadata/tracked_sats','I',('timestamps'))
    used_sats    = f.createVariable('GPS/metadata/used_sats','I',('timestamps'))
    soln_status  = f.createVariable('GPS/metadata/solution_status','I',('timestamps'))
    soln_type    = f.createVariable('GPS/metadata/solution_type','I',('timestamps'))
    latency      = f.createVariable('GPS/metadata/latency','f4',('timestamps'))



    # here's where you should loop over multiple GPS timestamp messages:
    i=0
    G = data['G']
    lat[i] = G['lat']
    lon[i] = G['lon']
    alt[i] = G['alt']

    v_horiz[i] = G['horiz_speed']
    v_vert[i] = G['vert_speed']
    v_gt[i] = G['ground_track']

    # GPS metadata
    tracked_sats[i] = G['tracked_sats']
    used_sats[i] = G['used_sats']
    soln_status[i] = G['solution_status']
    soln_type[i] = G['solution_type']
    latency[i] = G['latency']
    f.close()


if __name__ == '__main__':

    import os
    import pickle
    with open("decoded_data.pkl",'rb') as f:
        outs = pickle.load(f)

    # os.remove('survey_data.nc')
    print("writing survey data")
    write_survey_netCDF(outs['survey'])

    print("writing burst data")
    write_burst_netCDF(outs['burst'][0])