import requests
import datetime
import os

url = 'https://celestrak.com/satcat/tle.php?CATNR=45120'
outfile=os.path.join('resources','VPM_TLE.txt')


r = requests.get(url, allow_redirects=True)
s = r.content.split(bytes('\r\n','utf-8'))[1:]

print('VPM TLE:')
print(s)
with open(outfile,'wb') as file:
	for x in s:
		file.write(x)
		file.write(bytes('\n','utf-8'))




# 9-14-2020: Here's how you update the JSON file:

#1 ) go to space-track.org
#2 ) log in
#3 ) go to the following URL:
# https://www.space-track.org/basicspacedata/query/class/tle/NORAD_CAT_ID/45120/orderby/EPOCH asc/
# This will pull down a JSON file with all the available TLE entries for VPM (NORAD 45120)