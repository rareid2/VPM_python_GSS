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
  --in_dir IN_DIR       path to directory of .TLM files
  --out_dir OUT_DIR     path to output directory
  --workfile WORKFILE   file to store unused packets (a pickle file)
  --previous_pkl_file PREVIOUS_PKL_FILE
                        filename of previously-decoded packets (packets.pkl)
  --save_xml            save decoded data in XML files
  --no_xml              do not generate output XML files
  --save_pkl            save decoded data as python Pickle files
  --no_pkl              do not generate output pickle files
  --include_previous_data
                        Load and include previously-decoded data, which was
                        not processed
  --ignore_previous_data
                        Do not include previously-decoded, but unprocessed
                        data
  --move_completed      move completed .TLM files to the <out_dir>/processed
  --ignore_survey       Ignore any survey data
  --ignore_burst        Ignore any burst data
  --debug               Debug mode (extra chatty)
  --packet_inspector    Show the packet inspector tool
  --interactive_plots   Show plots
  ```
  

### Requirements:
  - python 3
  - numpy
  - matplotlib
  - basic python libraries (os, logging, etc)
  
  (I'm using Anaconda3)
