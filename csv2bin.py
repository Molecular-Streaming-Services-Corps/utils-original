"""
python3 csv2bin.py --in ../signals/1B_blood_floats.csv --out 1bfloat.bin --range=200na
python3 offline_data_viewer_gui.py --bin 1bfloat.bin
"""
#!/usr/bin/python3

import argparse
import struct
import csv
import re

parser = argparse.ArgumentParser(description='Convert CSV to raw binary data file')
parser.add_argument('--in', dest='in', action='store',
                    help='CSV filename to read')

parser.add_argument('--out', dest='out', action='store',
                    help='binary filename to save')

parser.add_argument('--range', dest='range', action='store',
                    help='input CSV contains float values, and the specified current range is used to scale to INT16 (i.e arg of 200na equates to +/-200nA or +/- 32768 INT16')


args = parser.parse_args()
values=vars(args)

inf=values["in"]
outf=values["out"]
_range=values["range"]
if _range:
	range_regex  = re.compile(r'(\d+)(.+)')
	match = range_regex.match(_range)
	print(match.group(1))
	_range_num = int(match.group(1))
	_range_amp = match.group(2)
	print(_range_num, _range_amp)
	halfshort = (2**16)/2
	def func(x):
		v = int((float(x)/_range_num)*halfshort)
		#print(v)
		return struct.pack('<h', v)
else:
	halfshort = (2**16)/2
	func = lambda x: struct.pack('>h', int(x))


with open(inf) as csvfile:
	with open(outf, 'wb') as outfile:
	    csv_reader = csv.reader(csvfile, delimiter=',')
	    # for i, line in enumerate(csv_reader):
	    for line in csv_reader:
	        # volts = float(line[2])
	        # if not volts:
	        #     continue

	        try:
	        	# print(i)
	        	val = func(line[1])
	        	#print('\t',line[1], '\t', val, '\n')
	        	outfile.write(val)
	        except struct.error:
	        	print(line[1])
	        	raise
	        # if i==14:
	        # 	break
