#/bin/bash

python process_packets.py

python process_status_data.py
python process_survey_data.py
python generate_survey_quicklooks.py
python process_burst_data.py