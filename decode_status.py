import numpy as np
import pickle
import datetime
from decode_burst_command import decode_burst_command, decode_uBBR_command
import logging


def decode_status(packets):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Locates any "status" packets, and prints a nicely-formatted string.

    inputs: 
        packets: A list of "packet" dictionaries, as returned from decode_packets.py
    outputs:
        A list of dictionaries, containing all the keys + values from the status message.
        Use "print_status(list)" to print a nice string
    '''

    logger = logging.getLogger(__name__)

    out_data = []

    # get status packets    
    for p in filter(lambda packet: packet['dtype'] == 'I', packets):
        try:
            data = p['data'][:p['bytecount']]

            source = chr(data[3])
            prev_command = np.flip(data[0:3])
            prev_bbr_command = np.flip(data[4:7])
            prev_burst_command = np.flip(data[12:15])
            total_commands = data[16] + 256*data[17]
            
            system_config = np.flip(data[20:24])

            # Cast it to a binary string
            system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')

            gps_resets = int(system_config[29:32],base=2)
            e_deployer_counter = int(system_config[0:4],base=2)
            b_deployer_counter = int(system_config[4:8],base=2)
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

            burst_pulses = int(system_config[16:24],base=2)

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

            # # Decode the burst command:
            # cfg = decode_burst_command(prev_burst_command)

            out_dict = dict()
            out_dict['header_timestamp'] = p['header_timestamp']
            out_dict['source'] = source
            out_dict['prev_command'] = prev_command
            out_dict['prev_bbr_command'] = prev_bbr_command
            out_dict['prev_burst_command'] = prev_burst_command
            out_dict['total_commands'] = total_commands
            out_dict['gps_resets'] = gps_resets
            out_dict['e_deployer_counter'] = e_deployer_counter
            out_dict['b_deployer_counter'] = b_deployer_counter
            out_dict['arm_e'] = arm_e
            out_dict['arm_b'] = arm_b
            out_dict['gps_enable'] = gps_enable
            out_dict['e_enable'] = e_enable
            out_dict['b_enable'] = b_enable
            out_dict['lcs_enable'] = lcs_enable
            out_dict['survey_period'] = survey_period
            out_dict['burst_pulses'] = burst_pulses
            out_dict['survey_total'] = survey_total
            out_dict['E_total'] = E_total
            out_dict['B_total'] = B_total
            out_dict['LCS_total'] = LCS_total
            out_dict['GPS_total'] = GPS_total
            out_dict['status_total'] = status_total
            out_dict['E_exp_num'] = E_exp_num
            out_dict['B_exp_num'] = B_exp_num
            out_dict['LCS_exp_num'] = LCS_exp_num
            out_dict['GPS_exp_num'] = GPS_exp_num
            out_dict['survey_exp_num'] = survey_exp_num
            out_dict['uptime'] = uptime
            out_dict['total_bytes_out'] = total_bytes_out
            out_dict['bytes_in_memory'] = bytes_in_memory
            out_dict['GPS_errors'] = GPS_errors
            out_dict['mem_percent_full'] = mem_percent_full

            out_dict['burst_config'] = decode_burst_command(prev_burst_command)
            out_dict['bbr_config'] = decode_uBBR_command(prev_bbr_command)

            # out_data.append(nice_str)
            out_data.append(out_dict)

        except:
            logger.warning(f'Failed to decode a status packet')
    return out_data

def print_status(data_list):
    ''' Prints a nicely-formatted status message, from a list of status dictionaries '''

    for d in data_list:
        
                    # Decode the burst command:
        cfg = decode_burst_command(d['prev_burst_command'])
        cmd_str = ""
        for k, v in cfg.items():
            if not "str" in k:
                cmd_str+= f"{k}={v}, "
        cmd_str = cmd_str[:-2]

        bbr = decode_uBBR_command(d['prev_bbr_command'])
        bbr_str = ""
        for k, v in bbr.items():
            bbr_str += f"{k}={v}, "
        bbr_str = bbr_str[:-2]

        nice_str = '---- System Status:  ----\n' +\
        'Packet received at:\t%s\n'%(datetime.datetime.utcfromtimestamp(d['header_timestamp'])) +\
        f"Source:\t\t\t{d['source']}\n" + \
        f"Uptime:\t\t\t{d['uptime']} Secs\n" +\
        f"Last Command:\t\t%s "%(''.join('{:02X} '.format(a) for a in d['prev_command'])) +\
        f" \t(%s)\n"%(''.join(str(chr(x)) for x in d['prev_command'])) +\
        f"Burst Command:\t\t%s "%(''.join('{:02X} '.format(a) for a in d['prev_burst_command'])) +\
        f" \t[%s]\n"%(''.join("|{0:8b}|".format(x) for x in d['prev_burst_command']).replace(' ','0')) +\
        "\t\t\t" + cmd_str + "\n" +\
        f"uBBR Command:\t\t%s "%(''.join('{:02X} '.format(a) for a in d['prev_bbr_command'])) +\
        f" \t[%s]\n"%(''.join("|{0:8b}|".format(x) for x in d['prev_bbr_command']).replace(' ','0')) +\
        "\t\t\t" + bbr_str + "\n" +\
        f"Total Commands:\t\t{d['total_commands']}\n" +\
        f"E channel enabled:\t{d['e_enable']}\n" +\
        f"B channel enabled:\t{d['b_enable']}\n" +\
        f"LCS enabled:\t\t{d['lcs_enable']}\n" +\
        f"GPS card enabled:\t{d['gps_enable']}\n"+\
        f"E antenna deploys:\t{d['e_deployer_counter']}\n" +\
        f"B antenna deploys:\t{d['b_deployer_counter']}\n" +\
        f"E deployer armed:\t{d['arm_e']}\n" +\
        f"B deployer armed:\t{d['arm_b']}\n" +\
        f"Survey period:\t\t{d['survey_period']}\n" +\
        f"Burst pulses:\t\t{d['burst_pulses']}\n" +\
        f"\nTotal Packets:\n" +\
        f"\tSurvey:\t\t{d['E_total']}\n" +\
        f"\tE burst:\t{d['E_total']}\n" +\
        f"\tB burst:\t{d['B_total']}\n" +\
        f"\tGPS burst:\t{d['GPS_total']}\n" +\
        f"\tStatus:\t\t{d['status_total']}\n" +\
        f"\tLCS:\t\t{d['LCS_total']}\n" +\
        f"Total transmitted data:\t{d['total_bytes_out']/1000} kb\n" +\
        f"Bytes in memory:\t{d['bytes_in_memory']/1000} kb\n" +\
        "Memory usage:\t\t{0:2.2f}%\n".format(d['mem_percent_full']) +\
        "\nCurrent experiment numbers:\n" +\
        f"\tSurvey:\t\t{d['survey_exp_num']}\n" +\
        f"\tE:\t\t{d['E_exp_num']}\n" +\
        f"\tB:\t\t{d['B_exp_num']}\n" +\
        f"\tGPS:\t\t{d['GPS_exp_num']}\n" +\
        f"\tLCS:\t\t{d['LCS_exp_num']}\n" +\
        f"\nGPS errors:\t\t{d['GPS_errors']}\n" +\
        f"GPS restart:\t\t{d['gps_resets']}\n"

        print(nice_str)
        print('\n')

        decode_uBBR_command(d['prev_bbr_command'])


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
    from file_handlers import write_status_XML
    with open('output/packets.pkl','rb') as f:
        packets = pickle.load(f)

    stats = decode_status(packets)
    print_status(stats)
    write_status_XML(stats)
    # for stat in stats:
    #     print(stat)
    #     print("----------------------------------")
