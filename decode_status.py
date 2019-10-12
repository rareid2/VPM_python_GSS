import numpy as np
import pickle



def decode_status(packets):
    ''' Locate any "status" packets, and print out a nicely formatted string 
    inputs: 
        packets: a list of packet dictionary objects
    '''


    # get status packets
    for p in filter(lambda packet: packet['dtype'] == 'I', packets):
        data = p['data'][:p['bytecount']]

        source = chr(data[3])
        prev_command = np.flip(data[0:3])
        prev_bbr_command = np.flip(data[4:7])
        prev_burst_command = np.flip(data[12:15])
        total_commands = data[16] + 256*data[17]
        
        system_config = np.flip(data[20:24])

        # Cast it to a binary string
        system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
        
        gps_resets = int(system_config[29:32],4)
        e_deployer_counter = int(system_config[0:4],4)
        b_deployer_counter = int(system_config[4:8],4)
        arm_e = int(system_config[13])
        arm_b = int(system_config[14])
        gps_enable = int(system_config[15])
        e_enable = int(system_config[26])
        b_enable = int(system_config[27])
        lcs_enable=int(system_config[28])

        if system_config[24]=='1':
            survey_period = 4096;
        elif system_config[25]=='1':
            survey_period = 2048;
        else:
            survey_period = 1024;

        burst_pulses = int(system_config[16:24],8)

        # print(gps_resets)
        survey_total = data[24] + pow(2,8)*data[25] + pow(2,16)*data[26] + pow(2,24)*data[27];
        E_total = data[28] + pow(2,8)*data[29] + pow(2,16)*data[30] + pow(2,24)*data[31];
        B_total = data[32] + pow(2,8)*data[33] + pow(2,16)*data[34] + pow(2,24)*data[35];
        LCS_total = data[36] + pow(2,8)*data[37] + pow(2,16)*data[38] + pow(2,24)*data[39];
        GPS_total = data[40] + pow(2,8)*data[41] + pow(2,16)*data[42] + pow(2,24)*data[43];
        status_total = data[44] + pow(2,8)*data[45] + pow(2,16)*data[46] + pow(2,24)*data[47];
        E_exp_num = data[51];
        B_exp_num = data[50];
        LCS_exp_num = data[49];
        GPS_exp_num = data[48];
        survey_exp_num = data[55];
        uptime = data[56]+ pow(2,8)*data[57] + pow(2,16)*data[58] + pow(2,24)*data[59]
        total_bytes_out = data[60] + pow(2,8)*data[61] + pow(2,16)*data[62] + pow(2,24)*data[63];
        bytes_in_memory = 4*(data[64] + pow(2,8)*data[65] + pow(2,16)*data[66] + pow(2,24)*data[67]);
        GPS_errors = data[68] + pow(2,8)*data[69];

        mem_percent_full = 100.*(bytes_in_memory)/(128.*1024*1024);

        nice_str = '---- System Status:  ----\n' +\
                f'Source:\t\t\t{source}\n' + \
                f'Uptime:\t\t\t{uptime} Secs\n' +\
                f'Last Command:\t\t%s '%(''.join('{:02X} '.format(a) for a in prev_command)) +\
                f' \t(%s)\n'%(''.join(str(chr(x)) for x in prev_command)) +\
                f'Burst Command:\t\t%s '%(''.join('{:02X} '.format(a) for a in prev_burst_command)) +\
                f' \t[%s]\n'%(''.join("|{0:8b}|".format(x) for x in prev_burst_command).replace(' ','0')) +\
                f'uBBR Command:\t\t%s '%(''.join('{:02X}'.format(a) for a in prev_bbr_command)) +\
                f' \t[%s]\n'%(''.join("|{0:8b}|".format(x) for x in prev_bbr_command).replace(' ','0')) +\
                f'Total Commands:\t\t{total_commands}\n' +\
                f'E channel enabled:\t{e_enable}\n' +\
                f'B channel enabled:\t{b_enable}\n' +\
                f'LCS enabled:\t\t{lcs_enable}\n' +\
                f'GPS card enabled:\t{gps_enable}\n'+\
                f'E antenna deploys:\t{e_deployer_counter}\n' +\
                f'B antenna deploys:\t{b_deployer_counter}\n' +\
                f'E deployer armed:\t{arm_e}\n' +\
                f'B deployer armed:\t{arm_b}\n' +\
                f'Survey period:\t\t{survey_period}\n' +\
                f'Burst pulses:\t\t{burst_pulses}\n' +\
                f'\nTotal Packets:\n' +\
                f'\tSurvey:\t\t{E_total}\n' +\
                f'\tE burst:\t{E_total}\n' +\
                f'\tB burst:\t{B_total}\n' +\
                f'\tGPS burst:\t{GPS_total}\n' +\
                f'\tStatus:\t\t{status_total}\n' +\
                f'\tLCS:\t\t{LCS_total}\n' +\
                f'Total transmitted data:\t{total_bytes_out/1000} kb\n' +\
                f'Bytes in memory:\t{bytes_in_memory/1000} kb\n' +\
                'Memory usage:\t\t{0:2.2f}%\n'.format(mem_percent_full) +\
                '\nCurrent experiment numbers:\n' +\
                f'\tSurvey:\t\t{survey_exp_num}\n' +\
                f'\tE:\t\t{E_exp_num}\n' +\
                f'\tB:\t\t{B_exp_num}\n' +\
                f'\tGPS:\t\t{GPS_exp_num}\n' +\
                f'\tLCS:\t\t{LCS_exp_num}\n' +\
                f'\nGPS errors:\t\t{GPS_errors}\n' +\
                f'GPS restart:\t\t{gps_resets}\n'
                

        # Print it. I guess we could return these instead...

        print(nice_str)
if __name__ == '__main__':

    with open('packets.pkl','rb') as f:
        packets = pickle.load(f)

    decode_status(packets)