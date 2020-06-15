import os
import csv

def get_last_access_time(log_name, source_str):
    
    # if not os.path.exists(log_name):
    if not os.path.exists(log_name):
        return 0
    else: 
        with open(log_name, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader if source_str in row[2]]
        
        if rows:
            return max([float(r[0]) for r in rows])
        else:
            return 0
        

def log_access_time(log_name, source_str, desc_str=''):
        
    if not os.path.exists(log_name):
        with open(log_name,'w') as csvfile:
            csvfile.write('timestamp,time_str,source,description\n')
        
    t = datetime.datetime.now()

    with open(log_name,'a') as csvfile:
        csvfile.write(f"{t.timestamp()},{t.isoformat()},{source_str},{desc_str.replace(',',';')},\n")

