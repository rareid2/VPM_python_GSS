import netCDF4
import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
import numpy as np
import datetime

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
    for i, d in enumerate(sorted(outs['survey'], key = lambda i: i['GPS'][0]['timestamp'])):
        E[i,:] = d['E_data']
        B[i,:] = d['B_data']

        T[i] = d['GPS'][0]['timestamp']

        lat[i] = d['GPS'][0]['lat']
        lon[i] = d['GPS'][0]['lon']
        alt[i] = d['GPS'][0]['alt']
        
        v_horiz[i] = d['GPS'][0]['horiz_speed']
        v_vert[i]  = d['GPS'][0]['vert_speed']
        v_gt[i]    = d['GPS'][0]['ground_track']

        # GPS metadata
        tracked_sats[i] = d['GPS'][0]['tracked_sats']
        used_sats[i]    = d['GPS'][0]['used_sats']
        soln_status[i]  = d['GPS'][0]['solution_status']
        soln_type[i]    = d['GPS'][0]['solution_type']
        latency[i]      = d['GPS'][0]['latency']

    f.close()


def write_burst_netCDF(data, filename='burst_data.nc'):

    datatype = 'int16' # single, double? int? The original data is 16 bit

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
        
        T = f.createVariable('data/t_axis','f4',('time'))
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

        T = f.createVariable('data/t_axis','f4',('time'))
        T.description = "time axis (seconds elapsed from beginning of burst)"
        T[:] = data['t_axis']
        
        F = f.createVariable('data/f_axis','f4',('freq'))
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
    for i, G in enumerate(data['G']):
    
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


def write_survey_XML(in_data, filename='survey_data.xml'):
    ''' Write a list of survey elements to an xml file. '''
    
    # Sort by internal timestamp    
    # in_data = sorted(in_data, key=lambda k: k['GPS'][0]['timestamp'])
    # Sort by receipt timestamp
    in_data = sorted(in_data, key=lambda k: k['header_timestamp'])

    d = ET.Element('survey_data')
    # d.set('creation_date', str(datetime.datetime.now(datetime.timezone.utc).timestamp()))
    d.set('file_creation_date', datetime.datetime.now(datetime.timezone.utc).isoformat())

    for entry_data in in_data:
        entry = ET.SubElement(d, 'survey')
        E_elem = ET.SubElement(entry, 'E_data')
        B_elem = ET.SubElement(entry, 'B_data')
        GPS_elem= ET.SubElement(entry,'GPS')
        E_elem.text = np.array2string(entry_data['E_data'], max_line_width=1000000000000, separator=',')[1:-2]
        B_elem.text = np.array2string(entry_data['B_data'], max_line_width=1000000000000, separator=',')[1:-2]


        for k, v in entry_data['GPS'][0].items():
            cur_item = ET.SubElement(GPS_elem,k)
            cur_item.text = str(v)
        header_entry = ET.SubElement(GPS_elem,'header_timestamp')
        header_entry.text = '{0:f}'.format(entry_data['header_timestamp'])

    rough_string = ET.tostring(d, 'utf-8')
    reparsed = MD.parseString(rough_string).toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(reparsed)

def read_survey_XML(filename):   
    ''' Reads survey elements from an xml file. '''

    # Open it
    with open(filename,'r') as f:
        tree = ET.parse(f)
    
    outs = []
    
    # Process all "survey" elements
    for S in tree.findall('survey'):
        d = dict()
        d['E_data'] = np.fromstring(S.find('E_data').text, dtype='uint8', sep=',')
        d['B_data'] = np.fromstring(S.find('B_data').text, dtype='uint8', sep=',')
        d['GPS'] = []
        d['GPS'].append(dict())
        G = S.find('GPS')
        for el in G:
            try:
                d['GPS'][0][el.tag] = int(el.text)
            except:
                d['GPS'][0][el.tag] = float(el.text)
        outs.append(d)

    # Return a list of dicts
    return outs


def write_burst_XML(in_data, filename='burst_data.xml'):
    ''' write a list of burst elements to an xml file. '''
    in_data = sorted(in_data, key=lambda k: k['header_timestamp'])

    d = ET.Element('burst_data')
    d.set('file_creation_date', datetime.datetime.now(datetime.timezone.utc).isoformat())

    for entry_data in in_data:
        entry = ET.SubElement(d, 'burst')
        entry.set('header_timestamp',datetime.datetime.utcfromtimestamp(entry_data['header_timestamp']).isoformat())
        cfg = ET.SubElement(entry, 'config')
        gps = ET.SubElement(entry, 'GPS')
        for k, v in entry_data['config'].items():
            cur_item = ET.SubElement(cfg,k)
            cur_item.text = str(v)

        for g in entry_data['G']:
            gps_el = ET.SubElement(gps,'gps_entry')
            for k, v in g.items():
                cur_item = ET.SubElement(gps_el,k)
                cur_item.text = str(v)


        if entry_data['config']['TD_FD_SELECT']==1:
            # Time domain
            E_data_elem = ET.SubElement(entry,'E_data')
            E_data_elem.set('mode','time domain')
            E_str = ''.join(['{0:g},'.format(x) for x in entry_data['E']])[0:-1]
            E_data_elem.text = E_str
            B_data_elem = ET.SubElement(entry,'B_data')
            B_data_elem.set('mode','time domain')
            B_str = ''.join(['{0:g},'.format(x) for x in entry_data['B']])[0:-1]
            B_data_elem.text = B_str

        if entry_data['config']['TD_FD_SELECT']==0:
            # Frequency domain
            E_data_elem = ET.SubElement(entry,'E_data')
            E_data_elem.set('mode','frequency domain')
            E_real = ET.SubElement(E_data_elem,'real')
            E_imag = ET.SubElement(E_data_elem,'imag')

            E_str = ''.join(['{0:g},'.format(np.real(x)) for x in entry_data['E']])[0:-1]
            E_real.text = E_str
            E_str = ''.join(['{0:g},'.format(np.imag(x)) for x in entry_data['E']])[0:-1]
            E_imag.text = E_str

            B_data_elem = ET.SubElement(entry,'B_data')
            B_data_elem.set('mode','frequency domain')
            B_real = ET.SubElement(B_data_elem,'real')
            B_imag = ET.SubElement(B_data_elem,'imag')

            B_str = ''.join(['{0:g},'.format(np.real(x)) for x in entry_data['B']])[0:-1]
            B_real.text = B_str
            B_str = ''.join(['{0:g},'.format(np.imag(x)) for x in entry_data['B']])[0:-1]
            B_imag.text = B_str


    rough_string = ET.tostring(d, 'utf-8')
    reparsed = MD.parseString(rough_string).toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(reparsed)



def read_burst_XML(filename):   
    ''' Reads burst elements from an xml file. '''

    # Open it
    with open(filename,'r') as f:
        tree = ET.parse(f)
    
    outs = []
    
    # Process all "survey" elements
    for S in tree.findall('burst'):
        d = dict()
        ER = np.fromstring(S.find('E_data').find('real').text, dtype='int16', sep=',')
        EI = np.fromstring(S.find('E_data').find('imag').text, dtype='int16', sep=',')
        d['E_data'] = ER + 1j*EI
        
        BR = np.fromstring(S.find('B_data').find('real').text, dtype='int16', sep=',')
        BI = np.fromstring(S.find('B_data').find('imag').text, dtype='int16', sep=',')
        d['B_data'] = BR + 1j*BI


        d['GPS'] = []
        G = S.findall('GPS')

        for el in G:
            try:
                d['GPS'][el.tag] = int(el.text)
            except:
                d['GPS'][el.tag] = float(el.text)
        outs.append(d)

    # Return a list of dicts
    return outs


if __name__ == '__main__':

    import os
    import pickle
    with open("decoded_data.pkl",'rb') as f:
        outs = pickle.load(f)


    # os.remove('survey_data.nc')
    # print("writing survey data")
    # write_survey_netCDF(outs['survey'])
    # write_survey_XML(outs['survey'])

    print("writing burst data")
    write_burst_XML(outs['burst'])
    # write_burst_netCDF(outs['burst'][0])