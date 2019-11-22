# VPM_python_GSS
VPM Ground Support Software (python version)

Python software to decode data from VPM.


### To run the test:
  The main program is "process_VPM_data.py".
  
  A basic run of this script is called using:
  
  ```python process_VPM_data.py --in_dir=<input data directory>```
  
  Several command line options are available; to see them, call:
  ```python process_VPM_data.py --help```
  
  Current flags:
  ```
usage: process_VPM_data.py [-h] [--in_dir IN_DIR] [--out_dir OUT_DIR]
                           [--workfile WORKFILE]
                           [--previous_pkl_file PREVIOUS_PKL_FILE] [--t1 T1]
                           [--t2 T2] [--burst_cmd BURST_CMD]
                           [--n_pulses N_PULSES] [--logfile LOGFILE]
                           [--no_xml] [--save_pkl] [--save_netcdf]
                           [--ignore_previous_data] [--move_completed]
                           [--ignore_survey] [--ignore_burst] [--debug]
                           [--packet_inspector] [--interactive_plots]
                           [--identify_bursts_by_status_packets]

VPM Ground Support Software

optional arguments:
  -h, --help            show this help message and exit
  --in_dir IN_DIR       path to directory of .tlm files
  --out_dir OUT_DIR     path to output directory
  --workfile WORKFILE   file to store unused packets (a pickle file)
  --previous_pkl_file PREVIOUS_PKL_FILE
                        filename of previously-decoded packets to process,
                        rather than a directory of .TLM files (packets.pkl)
  --t1 T1               burst packet start time. MM-DD-YYYYTHH:MM:SS
  --t2 T2               burst packet stop time. MM-DD-YYYYTHH:MM:SS
  --burst_cmd BURST_CMD
                        Manually-assigned burst command, in hex; overrides any
                        found commands
  --n_pulses N_PULSES   Manually-assigned burst_pulses; overrides any found
                        commands
  --logfile LOGFILE     log filename. If not provided, output is logged to
                        console
  --no_xml              do not generate output XML files
  --save_pkl            save decoded data as python Pickle files
  --save_netcdf         save decoded data in netCDF files
  --ignore_previous_data
                        Do not include previously-decoded but unprocessed data
                        (packets stored in WORKFILE)
  --move_completed      move completed .TLM files to the <out_dir>/processed
  --ignore_survey       Ignore any survey data
  --ignore_burst        Ignore any burst data
  --debug               Debug mode (extra chatty)
  --packet_inspector    Show the packet inspector tool
  --interactive_plots   Show plots interactively
  --identify_bursts_by_status_packets
                        Identify burst experiments using status packets, which
                        are sent before and after each burst
  ```
  

### Requirements:
  - python 3
  - numpy
  - matplotlib
  - basic python libraries (os, logging, etc)
  - netcdf4, if saving netCDF files
  
  (I'm using Anaconda3)
