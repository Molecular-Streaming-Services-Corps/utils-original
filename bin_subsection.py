#!/usr/bin/python3
from teensy_gui.command_line_user_interface import get_binary_file_offset_from_seconds
import argparse
import struct

parser = argparse.ArgumentParser(description='Convert raw binary data file to viewable')
parser.add_argument('in', action='store',
                    help='binary filename to read')
parser.add_argument('out', action='store',
                    help='binary filename to output')
parser.add_argument('start', action='store', type=int,
                    help='start byte (or second, if --freq is specified)')
parser.add_argument('end', action='store', type=int,
                    help='end byte (or second, if --freq is specified)')
parser.add_argument("--freq", type=float)


args = parser.parse_args()
values=vars(args)
print(values)

infilename=values["in"]
outfilename=values["out"]
start = values['start']
end = values['end']


if values['freq']:
    print('processing offsets as seconds')
    start = get_binary_file_offset_from_seconds(start, values['freq'])
    end = get_binary_file_offset_from_seconds(end, values['freq'])

assert (end>start), "start must be less than end!"

with open(infilename, 'rb') as file_to_read:
    with open(outfilename, 'wb') as file_to_save:
        print(f'seeking to {start} in file')
        file_to_read.seek(start)
        data = file_to_read.read(end-start)
        file_to_save.write(data)