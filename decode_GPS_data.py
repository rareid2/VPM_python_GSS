import numpy as np
import pickle
import datetime
from VPM_data_functions import find_sequence

def decode_GPS_data(data):
    leap_seconds = 18  # GPS time does not account for leap seconds; as of ~2019, GPS leads UTC by 18 seconds.
    reference_date = datetime.datetime(1980,1,6,0,0,0)
    pos_inds = find_sequence(data,np.array([0xAA, 0x44, 0x12, 0x1C, 0x2A]))
    vel_inds = find_sequence(data,np.array([0xAA, 0x44, 0x12, 0x1C, 0x63]))
    
    print(f'found {len(pos_inds)} position logs and {len(vel_inds)} velocity logs')
#     print(data.astype('int'))
    week_ind = 14;
    sec_ind = 16;
    header_len = 28;
    tracked_ind = 63;
    used_ind = 64;
    

    tracked_sats = int(data[pos_inds + header_len + tracked_ind])
    used_sats = int(data[pos_inds + header_len + used_ind])
    
    weeknums_pos = 1.0*(data[pos_inds + week_ind] + 256*data[pos_inds + week_ind + 1]);
    weeknums_vel = 1.0*(data[vel_inds + week_ind] + 256*data[vel_inds + week_ind + 1]);
    
    sec_offset_pos =(data[pos_inds + sec_ind] + 256*data[pos_inds + sec_ind +1] +\
        pow(2,16)*data[pos_inds + sec_ind + 2] + pow(2,24)*data[pos_inds + sec_ind + 3]).astype('int32')/1000.
    sec_offset_vel =(data[vel_inds + sec_ind] + 256*data[vel_inds + sec_ind +1] +\
        pow(2,16)*data[vel_inds + sec_ind + 2] + pow(2,24)*data[vel_inds + sec_ind + 3]).astype('int32')/1000.

    # print(weeknums_pos)
    # print(sec_offset_pos)
    if (sec_offset_pos != sec_offset_vel) or (weeknums_pos != weeknums_vel):
        # TBH, this really shouldn't happen unless there's data corruption
        print("Position / Velocity message mismatch!")
    
    d = reference_date + datetime.timedelta(weeks=weeknums_pos[0]) + datetime.timedelta(seconds=sec_offset_pos[0]) 
    
    gps_decoded = dict()
    gps_decoded['time'] = d
    gps_decoded['weeknum'] = weeknums_pos
    gps_decoded['sec_offset'] = sec_offset_pos
    gps_decoded['tracked_sats'] = tracked_sats
    gps_decoded['used_in_solution'] = used_sats
    
    return gps_decoded