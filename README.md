# VPM_python_GSS
VPM Ground Support Software (python version)

Python software to decode data from VPM.
## To use the automated processing scripts:

#### run ```./automate.sh```


  ##### Automated processing is accomplished in five separate modules:
   1. ```process_packets.py```
   
      This module decodes any new telemetry files, and stores them into a searchable database.
   2. ```process_status_data.py```
   
      This module searches the database from (1), and outputs status entries to a file tree.
   3. ```process_survey_data.py```
   
      This module searches the database from (1), and outputs survey products to a file tree, in .xml, .mat, or .pkl formats
  
   4. ```generate_survey_quicklooks.py```
      This module loads survey data from an XML file tree, and generates quicklook plots in .png format, for a specified time cadence.
      
   5. ```process_burst_data.py```
      This module loads packets from (1), and decodes burst experiments, by grouping burst data packets between header/footer status packets. Incomplete bursts (especially those missing the header or footer) will be missed, and will need to be decoded manually. Also plots spectrograms and, if GPS data is available, a map.
      
### Configuration and Logging:
##### Configurable parameters are in ```GSS_settings.conf```

##### db_locations:

  1. telemetry_watch_directory:

      The directory to watch for new telemetry files. Any CSV or TLM files will be decoded and stored in the packet database. Can be a comma-separated list. The tree is walked to search any subfolders as well. Each telemetry file must have a unique file name, as only one file of each name will be processed.

  2. ```packet_db_file, survey_tree_root, burst_tree_root, status_tree_root```
      The paths to the various output directories -- survey, burst, and status file trees, and the packet database file.
      
##### survey_config
  
  1.  ```file_types```: output file format. XML, matlab, or pickle. comma-separated list.

  2.  ```plot_length```: The length of the plot, in hours. 3 to 12 seems good.
  
  3.  ```dpi```: output plot dots per inch.
  
  4.  ```line_plots```: The different metadata fields to plot alongside the E and B spectrograms.
  
 ##### burst_config

  1.  ```file_types```: output file format. XML, matlab, or pickle. comma-separated list.
  
  2.  ```do_plots, do_maps```: output plots (time and spectrogram), and if GPS data is available, location maps.
  
  3.  ```dpi```: output plot dots per inch.
  
  4.  ```calibration_file```: Calibration data to load. If the uBBR status is available, the burst data will be plotted in calibrated units.
  
  5.  ```TX_file```: A configurable list of transmitter locations to plot on the map.
  
  6.  ```TLE_file```: The satellite TLE, for plotting extended ground tracks. This will need to be updated periodically as the orbit changes.

##### logging
  1.  ```log_level```: The output verbosity: WARNING, INFO, DEBUG, EXCEPTION
 
  2.  ```log_file```: Where to log the output. If blank, print to the console.
  
  3.  ```access_log```: An auto-generated log of last-run times, so we don't have to process the whole set every single time. If there's trouble and we need to rerun things, you might need to delete some entries in here.
  
### To process individual cases from the command line:
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
  - basemap
  - pyephem
 

Anaconda 3 gets all the requirements, except for ephem (```pip install pyephem```) and basemap (```conda install -c anaconda basemap```)
