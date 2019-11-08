import numpy as np
import matplotlib.pyplot as plt
import datetime
import os
import pickle
from decode_status import decode_status
from decode_burst_command import decode_burst_command

def packet_inspector(packets):
    ''' A nice tool to analyze packets in a list. CLick'em to see info about them! '''

    # Select burst packets
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets = list(filter(lambda packet: packet['dtype'] == 'I', packets))
    S_packets = list(filter(lambda packet: packet['dtype'] == 'S', packets))
    
    print(f'E: {len(E_packets)} B: {len(B_packets)} G: {len(G_packets)} Status: {len(I_packets)} Survey: {len(S_packets)}')  
    print("Exp nums:",np.unique([p['exp_num'] for p in packets]))
    print("Burst exp nums:",np.unique([p['exp_num'] for p in E_packets + B_packets + G_packets]))
    print("Survey exp nums:",np.unique([p['exp_num'] for p in S_packets]))



    # -------- arrival time debugging plot -------
    fig, ax = plt.subplots(1,1)
    taxis = np.arange(len(packets))    
    tstamps = np.array([p['header_timestamp'] for p in packets])
    dtypes  = np.array([p['dtype'] for p in packets])

    ax.plot(taxis[dtypes=='E'], tstamps[dtypes=='E'],'.', label='E',      picker=5)
    ax.plot(taxis[dtypes=='B'], tstamps[dtypes=='B'],'.', label='B',      picker=5)
    ax.plot(taxis[dtypes=='G'], tstamps[dtypes=='G'],'.', label='GPS',    picker=5)
    ax.plot(taxis[dtypes=='I'], tstamps[dtypes=='I'],'o', label='Status', picker=5)
    ax.plot(taxis[dtypes=='S'], tstamps[dtypes=='S'],'.', label='Survey', picker=5)

    ax.hlines([p['header_timestamp'] for p in I_packets], 0, len(packets))
    ax.legend()
    ax.set_xlabel('arrival index')
    ax.set_ylabel('timestamp')

    fig.canvas.mpl_connect('pick_event', lambda event: onpick(event, packets))

    plt.show()

def onpick(event, packets):
    thisline = event.artist
    xdata = thisline.get_xdata()
    ydata = thisline.get_ydata()
    ind = event.ind
    x_inds = xdata[ind]
    print(x_inds)

    print(f"Clicked on {len(x_inds)} events")

    for x in x_inds:
        print(f'packet {x}:')
        print(f"\tdtype: {packets[x]['dtype']}")
        print(f"\theader timestamp: {packets[x]['header_timestamp']}" +\
        f" ({datetime.datetime.utcfromtimestamp(packets[x]['header_timestamp'])})")
        print(f"\tExp num: {packets[x]['exp_num']}")
        print(f"\tData indexes: [{packets[x]['start_ind']}:" +\
            f"{packets[x]['start_ind'] + packets[x]['bytecount']}]")

        if packets[x]['dtype']=='I':
            stat = decode_status([packets[x]])
            print(stat[0])

        if (packets[x]['dtype']=='G') and (packets[x]['start_ind']==0):
            # First GPS packet -- burst command is echoed here
            cmd = np.flip(packets[x]['data'][0:3])
            burst_config = decode_burst_command(cmd)
            print(burst_config)


if __name__ == '__main__':

    with open('output/packets.pkl','rb') as f:
        packets = pickle.load(f)

    packet_inspector(packets)
