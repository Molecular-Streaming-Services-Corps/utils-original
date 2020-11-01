#!/usr/bin/python3

import argparse
import struct

parser = argparse.ArgumentParser(description='Convert raw binary data file to viewable')
parser.add_argument('--in', dest='in', action='store',
                    help='binary filename to read')

args = parser.parse_args()
values=vars(args)

filename=values["in"]

infile = open(filename, 'rb');
data=infile.read(); # Foolishly read the whole thing into memory.

for i in range(0,len(data),2):
    print("%d, %d" % (i/2, struct.unpack('<h', data[i:i+2])[0]))

