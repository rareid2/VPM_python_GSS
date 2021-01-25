import os
"""
data_root = '/Users/rileyannereid/macworkspace/VPM_data/burst/mat/2020/08'

check_for_bursts = data_root

i = 0
for root, dirs, files in os.walk(check_for_bursts):
    for f in files:
        os.rename(root+'/'+f, data_root+'/'+f)
        
"""

# Reading an excel file using Python
import xlrd
 
# Give the location of the file
loc = ('/Users/rileyannereid/Downloads/VPM Full Database.xlsx')
 
# To open Workbook
wb = xlrd.open_workbook(loc)
sheet = wb.sheet_by_index(0)
 
# For row 0 and column 0
# goes to 196 
min_sum = 0
hour_sum = 0
count = 0
for i in range(3,197,1):
    timeval = sheet.cell_value(i, 1)
    if 'm' in timeval:
        for li, l in enumerate(timeval):
            if l == 'm':
                if '~' in timeval:
                    timevaln = timeval[1:li-1].strip()
                else:
                    timevaln = timeval[:li-1].strip()
                time_int = float(timevaln)
                min_sum+=time_int
                count+=1
                continue
    if 'h' in timeval:
        for li, l in enumerate(timeval):
            if l == 'h':
                if '~' in timeval:
                    timevaln = timeval[1:li-1].strip()
                else:
                    timevaln = timeval[:li-1].strip()
                time_int = float(timevaln)
                hour_sum+=time_int
                count+=1
                continue

print(hour_sum + min_sum/60)
print(count)
