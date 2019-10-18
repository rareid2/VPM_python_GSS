import numpy as np
import pickle
from scipy.io import loadmat
import os
import json

from decode_packets import decode_packets
from decode_survey_data import decode_survey_data
from decode_burst_data import decode_burst_data
from decode_status import decode_status
from plot_survey_data import plot_survey_data
from plot_burst_data import plot_burst_data


# An example script, showing how to use the decoding software:

# 1. Load the data (in this case, a Matlab file. This section will
   # be modified to digest VPM telemetry packets)
# inp_datafile = 'Data/Test 2-caltone.mat'
# mat_datafile = loadmat(inp_datafile, squeeze_me=True)
# raw_data = mat_datafile["outData_tones"].astype('uint8')
# print(np.shape(raw_data))

# Load data from a folder of .tlm files:
data_root = 'Data/ditl_cal'
d = os.listdir(data_root)
tlm_files = sorted([x for x in d if x.endswith('.tlm')])

raw_data = []
for fname in tlm_files:
    with open(os.path.join(data_root, fname),'rb') as f:
        cur_data = np.fromfile(f,dtype='uint8')
        raw_data.append(cur_data)

data = np.concatenate(raw_data).ravel()
print(np.shape(data))


# Decode the raw bytes into VPM packets
print('decoding packets...')
packets = decode_packets(data)

# Dump the decoded packets to a file
print('dumping to packets.pkl...')
with open('packets.pkl','wb') as f:
    pickle.dump(packets, f)

# Decode any survey data:
print("Decoding survey data")
S_data = decode_survey_data(packets)

# Decode any burst data:
print("Decoding burst data")
B_data = decode_burst_data(packets)

# Decode any status messages:
print("Decoding status messages")
stats = decode_status(packets)

for stat in stats:
	print(stat)

# Save the decoded data, so we can plot it:
# (Using Pickle for now; netCDF would be preferable for production)
outs = dict()
outs['survey'] = S_data
outs['burst'] = B_data
outs['status'] = stats

with open("decoded_data.pkl",'wb') as f:
	pickle.dump(outs, f)


print("plotting...")
plot_survey_data(S_data, "survey_data.pdf")
plot_burst_data(B_data, "burst_data.pdf")
