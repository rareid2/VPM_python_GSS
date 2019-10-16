import numpy as np
import pickle
from scipy.io import loadmat


from decode_packets import decode_packets
from decode_survey_data import decode_survey_data
from decode_burst_data import decode_burst_data
from decode_status import decode_status


# An example script, showing how to use the decoding software:

# 1. Load the data (in this case, a Matlab file. This section will
#    be modified to digest VPM telemetry packets)
inp_datafile = 'Data/Test 2-caltone.mat'
mat_datafile = loadmat(inp_datafile, squeeze_me=True)
mat_data = mat_datafile["outData_tones"].astype('uint8')

# Decode the raw bytes into VPM packets
print('decoding packets...')
packets = decode_packets(mat_data)

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
outs = dict()
outs['survey'] = S_data
outs['burst'] = B_data
outs['status'] = stats

with open("decoded_data.pkl",'wb') as f:
	pickle.dump(outs, f)