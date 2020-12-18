#!/usr/bin/env python3
"""
< little-endian  
> big-endian

Format C Type Python type Standard size Notes
x pad byte no value
c char string of length 1 1
b signed char integer 1 (3)
B unsigned char integer 1 (3) 
? _Bool bool 1 (1) 
h short integer 2 (3) 
H unsigned short integer 2 (3) 
i int integer 4 (3) 
I unsigned int integer 4 (3) 
l long integer 4 (3) 
L unsigned long integer 4 (3) 
q long long integer 8 (2), (3) 
Q unsigned long long integer 8 (2), (3) 
f float float 4 (4) 
d double float 8 (4) 
s char[] string 
p char[] string 
P void * integer (5), (3)
"""

import time
import queue
import socket
import struct
import argparse
from datetime import datetime
from threading import Thread, Event, Lock


valid_commands = {'set_pos': 1, 
                  'set_bias': 2, 
                  'start': 3, 
                  'stop': 6,
                  'error': ord('e'),
                  'test': 9,
                  'type_info': 9,
                  'send_TYPE_PORE_SAMPLES': 10}

sync = 0x16 # ASCI SYNC

# counts
_sync = 1
_body_count = 2
_type_code = 1
_sample_num = 8


def create_packet(msg_type, msg, samples_per_second=3E3, use_raw_protocol=False):
    if msg_type not in valid_commands:
        raise Exception(f'{msg_type} is not a valid command')
    msg_len = 0
    type_code = 0
    msg_data = []
    type_code = valid_commands[msg_type]
    if msg_type == 'set_pos':
        msg_data = struct.pack("d", msg)
    elif msg_type == 'set_bias':
        msg_data = struct.pack("d", msg)
    elif msg_type == 'start':
        bias = 0
        number_of_pores = 1
        samples_per_second = float(samples_per_second)
        # msg_data = [struct.pack("I", bias), struct.pack("I", number_of_pores), struct.pack("f", samples_per_second)]
        msg_data = [struct.pack(">I", number_of_pores), struct.pack(">f", samples_per_second),
                    b'' if not use_raw_protocol else b'1']
        print(f'start SAMPLE Hz {samples_per_second} data is : {msg_data}')
    elif msg_type == 'stop':
        pass
    elif msg_type == 'error':
        type_code = ord('e')
        msg_data = struct.pack("B", 0)
    elif msg_type == 'test':
        msg_data = bytes.fromhex('F00DF00D') #DEADBEEF
    elif msg_type == 'type_info':
        type_code = 9 #oops, clashes with above
        uint16_subid = struct.pack(">H", msg)
        if msg == 0:
            # mac_to_spoof = '04:e9:e5:0b:f1:80'
            # s = mac_to_spoof.encode('ascii')
            info = bytes([0x04, 0xe9, 0xe5, 0x0b, 0xf1, 0x80])
            #print(f'mac {info}')
        elif msg == 1:
            info = 'masquerador'.encode('ascii')
        elif msg ==2:
            info = 'fake_file.bin'.encode('ascii')
        msg_data = [uint16_subid, info]
        print(msg_data)
    elif msg_type == 'send_TYPE_PORE_SAMPLES':
        i,data = msg
        uint64_numbytes = struct.pack("<q", i)
        print(f'uint64_numbytes {uint64_numbytes}')
        msg_data = [uint64_numbytes, data]

    if not isinstance(msg_data, list):
        msg_len = len(msg_data)
        msg_data = [msg_data]
    else:
        msg_len = sum([len(b) for b in msg_data])

    msg_len += 1 # for the type-code, I think
    
    print('msg len is {}'.format(msg_len))

    body = b''.join([struct.pack("B", sync),
                     struct.pack(">H", msg_len),
                     struct.pack("B", type_code)] +
                     msg_data)
    return body


def process_return_data(cmd_type, data):
    int_cmd = int.from_bytes(cmd_type, 'big')
    if cmd_type == b'e':
        print(f'Error was: {data}')
    elif int_cmd == 9:
        print(f'test data was {data.hex()}')


def resync(buffer):
    for i in range(len(buffer)):
        SYNC = buffer[i]
        LENGTH = struct.unpack('>h', buffer[i+1:i+1+2])[0]
        if SYNC == sync and LENGTH<=100:
            del buffer[0:i]
            return

last_info = {}
def parse_raw_tcp_data(buffer):
    global last_info
    if len(buffer)<3:
        return
    data = None
    LENGTH = -1
    SYNC = buffer[0:_sync]
    if SYNC and SYNC[0] == sync:
        #print('got good sync')
        LENGTH = struct.unpack('>h', buffer[1:3])[0]
        #print(f'Received SYNC and LENGTH {LENGTH} with buflen {len(buffer)}')
        
        if (LENGTH>0) and len(buffer) >= 3+LENGTH:
            data = b''
            TYPE = buffer[3:4]
            data = buffer[3:3+LENGTH]
            #print(f'buflen {len(buffer)} TYPE {TYPE} LENGTH {LENGTH} data {data}')
            last_info = {'bytes': buffer[0:3+LENGTH], 'len':LENGTH, 'type':TYPE, 'data':data}
            del buffer[0:3+LENGTH]
    # if data is None:
        # print(f'No data properly detected SYNC {SYNC} LENGTH {LENGTH} buflen {len(buffer)} last {last_info} next 28 bytes: {buffer[0:28]}')
    return data


fake_data = range(0,2**16, 2**16//64)
_i = 0
fake_time = 0
def fake_rcv(rcv_len):
    global _i, fake_time
    typ=5
    _len = 11

    data_item = fake_data[_i]
    print(f'fake_rcv i ({_i}) ({data_item}) fake_time ({fake_time})')
    _i+=1
    if _i>=len(fake_data):
        _i = 0
    data = bytearray([sync,
                      (_len>>8)&0xff,
                      _len&0xff,
                      typ,
                      ])+ struct.pack('Q',fake_time)+ struct.pack('>H', data_item) # bytearray([
                      # data_item&0xff,
                      # (data_item>>8)&0xff])
    fake_time +=1
    return data


t=None
f=None
screen_display_buf_len = 512
def threaded_stream(HOST, PORT, 
                    screen_display_buffer_len=0, sample_rate_hz=3000,
                    # screen_refresh_rate=30,
                    save_filename=None, use_fake_data=False,
                    use_raw_protocol=False):
    """ screen_display_buffer_len = 0 means not outputting to screen
        save_filename - if "" (emtpy string) then filename will be auto-generated with a timestamp
    """
    global t
    global f
    print(f'threaded_stream Hz {sample_rate_hz}')
    if save_filename == '':
        save_filename = '{}.csv'.format(datetime.now().strftime('%m_%d_%Y__%H_%M_%S'))
    q = queue.SimpleQueue()
    q_lock = Lock()
    start_stop_event = Event()
    t = Thread(target=_threaded_pore_data_receive_stream,
               args=(q, q_lock, start_stop_event,
                     HOST, PORT,
                     #screen_display_buffer_len,
                     sample_rate_hz,
                     # screen_refresh_rate,
                     save_filename, use_fake_data, use_raw_protocol),
               daemon=True)
    t.start()
    return q, q_lock, start_stop_event


def ship_data(sample_num, value, save_file, q, q_lock):
    global screen_display_buf_len
    if save_file:
        save_file.write('{},{}\n'.format(sample_num,value))
    if screen_display_buf_len:
        if q.empty():
            q_lock.acquire()
        if q_lock.locked():# and q.qsize()<screen_display_buf_len:
            #print('added a frame worth')
            #q.get()
            #print(f'adding {sample_num}')
            q.put((sample_num, value))
            if q.qsize()>=screen_display_buf_len:
                # try:
                q_lock.release()
                # except RuntimeError as e:
                #     print('{} ****{}**** qsize {} screen_display_buf_len {}'.format(e, sample_num, q.qsize(), screen_display_buf_len))
        # if q.qsize()<screen_display_buf_len: 
        #     q.put((sample_num, value))
    # print(bool(unpack), bool(rcv), q.qsize())
    # now = datetime.now()
    # if (now-before).microseconds>(microseconds_between_display_updates) not q.full():
    #     #print(f'adding sample_num {sample_num}')
        
    #     # while not q.empty():
    #     #     time.sleep(0.0001)
    #     q.put(value, timeout=2)
    #     if q.full():
    #         before = now
    # else:
    #     pass
    #     #print('not time to display')

def _threaded_pore_data_receive_stream(q, q_lock, stop_streaming_event,
                     HOST, PORT,
                     #screen_display_buf_len,
                     sample_rate_hz,
                     # screen_refresh_rate,
                     save_filename, use_fake_data,
                     use_raw_protocol):
    global screen_display_buf_len
    last_sample_offset=0
    if not use_fake_data:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP uses SOCK_DGRAM
        try:
            print(f'attempting to connect to ({HOST}:{PORT})')
            s.connect((HOST, PORT))
        except OSError as e:
            stop_streaming_event.set()
            q.put(0)
            print(e)
            print('Try Again')
            return
    print('connected to host')
    command = 'start'
    sub_command = ''
    packet = create_packet(command, sub_command, sample_rate_hz, use_raw_protocol)
    print('sending start packet {}'.format(packet))
    if not use_fake_data:
        s.sendall(packet)
    rcv = bytearray()
    # print(id(stop_streaming_event))

    pre_data_offset = _sync + _body_count + _type_code + _sample_num
    _data_len = 2
    single_channel_packet_size = (pre_data_offset + _data_len)
    # if screen_display_buf_len:
    #     num_samples_per_download = screen_display_buf_len
    # else:
    #     num_samples_per_download = 1024
    #download_buf_size = (single_channel_packet_size * num_samples_per_download) * 20
    # microseconds_between_display_updates = 1E6//screen_refresh_rate
    #before = datetime.now()
    sample_num=0
    save_file = None
    error = None
    good_data = 0
    if save_filename:
        save_file = open(save_filename, 'w')

    while not stop_streaming_event.is_set():
        #print('threaded is set {}'.format(stop_streaming_event.is_set()))
        #now = datetime.now()
        # if not use_fake_data:
        #     b = b''
        #     while len(b)<download_buf_size:
        #         bytes_remaining_to_download = download_buf_size-len(b)
        #         #print(bytes_remaining_to_download)
        #         b += s.recv(bytes_remaining_to_download)
        # else:
        #     b = fake_rcv(0)
        chunk=b""
        try:
            chunk = s.recv(4096)
        except:
            pass

        rcv.extend(chunk)

        # if (now-before).microseconds<(1E6//30):
        #     while not q.empty():
        #         q.get()
        #     before = now
        #     continue
        # before = now
        # after = datetime.now()
        # if not use_fake_data:
        #     rcv.extend(b)
        # else:
        #     rcv += b
        # print(f'Received download_buf_size {download_buf_size}')
        # print('rcv is {}\n'.format(len(rcv)))#, rcv))
        #import pdb; pdb.set_trace()
        #diff = after-now
        #print('rcv SPS {}'.format((len(b)/2)/(diff.microseconds/1e6)+diff.seconds))
        #rcv.int.from_bytes(rcv_raw, 'little')
        unpack=True
        while unpack and rcv:
            #print(f'sample_num {sample_num}')
            #try:
            # rcv.read(2)
            data = parse_raw_tcp_data(rcv)
            if data:
                good_data +=1
                type_code = data[0]

                if type_code == 5:
                    try:
                        sample_num = struct.unpack('>Q', data[1:9])[0]
                        value = struct.unpack('>h', data[9:11])[0]
                    except struct.error as e:
                        print(e, data)
                    error = None
                    # print('type_code 5, datalen {}, len data is {}, #{}, val: {}'
                    #       .format(len(rcv), len(data), sample_num, value))
                    ship_data(sample_num, value, save_file, q, q_lock) #screen_display_buf_len
                elif type_code == 4: #TYPE_DATA_HEADER
                    data = data[1:]
                    delta_t = struct.unpack('>f', data[:4]); #float
                    npore = struct.unpack('>I', data[4:8]); #uint32
                    scale = struct.unpack('>f', data[8:12]); #float
                    print('sample data header: {}'.format(data))
                    print('delta T ({} seconds) number of active pores ({}) Amp/LSB ({})'
                          .format(delta_t, npore, scale))
                elif type_code == 10:
                    # raw pore samples
                    sample_number = struct.unpack('<Q', data[1:9])[0]

                    if (last_sample_offset != sample_number+1):
                        print(f"Missing data between {last_sample_offset} and {sample_number}!");

                    print("Got %d bytes of data starting at sample %d" % (len(data), sample_number))

                    offset=9
                    try:
                        while (offset < len(data)-1):
                            sample = struct.unpack('<H', data[offset:offset+2])[0] - 0x8000
                            last_sample_offset = sample_number
                            sample_number+=1
                            # if (csvfile):
                            #     csvfile.write(f"{last_sample_offset},{sample}\n")
                            # if (binfile):
                            #     binfile.write(struct.pack(">h", sample))
                            # if (not binfile) and (not csvfile):
                            #     print(f"Data  {last_sample_offset} {sample}")
                            offset += 2
                        # for value in vs:
                            ship_data(last_sample_offset, sample,
                                      save_file, q, q_lock) #screen_display_buf_len
                    except struct.error as e:
                        print(e)
                    print(offset, len(data))
                    unpack = False
                elif type_code == 9:
                    sub_id = struct.unpack('>h', data[1:3])[0]
                    data = data[3:]
                    if sub_id==0:
                        #mac = struct.unpack('<6B',data[1:])
                        print('MAC is:' + ':'.join(['%02x'% b for b in data]))
                    elif sub_id==1:
                        print('Version is: {}'.format(data[1:]))
                    else:
                        print('TYPE_INFO sub_id {}, data {}'.format(sub_id, data))
                else:
                    print(f'tc wasnt 5, it was {type_code}')
            else:
                unpack=False
                continue
                good_data = 0
                
                if len(rcv)>=14:
                    if not error:
                        print(f'data was none after {good_data} good packets, buflen now is {len(rcv)}')
                        # print(f'No data properly detected SYNC {SYNC} LENGTH {LENGTH} buflen {len(buffer)} last {last_info} next 28 bytes: {buffer[0:28]}')
                    # if not error:
                        print('resyncing')
                #     #stop_streaming_event.set()
                    resync(rcv)
                    #raise Exception('fail')
                error = True
                # unpack=False
                if len(rcv)<14:
                    unpack=False
                # del rcv[0:pre_data_offset+2]
            #print('sent {}'.format(v))
            # except struct.error as e:
            #     print(e)
            #     print('struct error, probably not enough bytes yet in buffer')
            #     unpack = False
            #     #raise
            #     #rcv_int = rcv[0+channel] | rcv[16+channel]<<8
            # except queue.Full as ee:
            #     print('q full')
            #     q.get()
            #     unpack=False
            # except Exception as eee:
            #     print(eee)
            #     unpack=False
    # send stop packet
    packet = create_packet('stop', sub_command, sample_rate_hz, use_raw_protocol)
    print('sending STOP packet {}'.format(packet))
    s.sendall(packet)
    s.setblocking(0)
    # wait for stop response
    while True:
        data = parse_raw_tcp_data(rcv)
        if data:
            # print('got data after stop requested')
            type_code = data[0]
            if type_code == 6: #TYPE_STOP
                print('Received STOP confirmation')
                break
            # else:
            #     print('looking for STOP but found {}'.format(type_code))
        chunk=b""
        try:
            chunk = s.recv(64)
        except:
            pass
        rcv.extend(chunk)
        # print(rcv)
    print('closing socket')
    # b = b''
#     while len(b)<download_buf_size:
#         bytes_remaining_to_download = download_buf_size-len(b)
#         #print(bytes_remaining_to_download)
#         b += s.recv(bytes_remaining_to_download)
    print('s.close')
    if not use_fake_data:
        s.close()
    if save_file:
        save_file.close()

def wait_for_sync(s):
    while True:
        try:
            SYNC = s.recv(1)
            if SYNC and SYNC[0] == sync:
                print('got good sync')
                LENGTH_UPPER = s.recv(1)
                LENGTH_LOWER = s.recv(1)
                TYPE = s.recv(1)
                print(SYNC)
                print(TYPE)
                print(LENGTH_UPPER)
                print(LENGTH_LOWER)
                LENGTH_UPPER = int.from_bytes(LENGTH_UPPER, byteorder='little')
                LENGTH_LOWER = int.from_bytes(LENGTH_LOWER, byteorder='little')
                print(f'LENGTH_UPPER {LENGTH_UPPER} LENGTH_LOWER {LENGTH_LOWER}')
                LENGTH = (LENGTH_UPPER<<8) | LENGTH_LOWER
                print(f'Received Type {TYPE} and LENGTH {LENGTH}')
                data = b''
                if (LENGTH-1):
                    data = s.recv(LENGTH - 1)
                    print(f'Received data: {data}')
                return (TYPE, data)
        except:
            pass

def masquerade(server='lilith.demonpore.tv', port=31416, filepath_to_stream='1b_blood.bin'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP uses SOCK_DGRAM
    try:
        print(f'attempting to connect to ({server}:{port})')
        s.connect((server, port))
    except OSError as e:
        print(e)
        print('Try Again')
        return
    print(f'connected to {server}')
    
    packet = create_packet('type_info', 0)

    print('sending info MAC packet {}'.format(packet))
    s.sendall(packet)
    packet = create_packet('type_info', 1)
    print('sending info VERSIOn packet {}'.format(packet))
    s.sendall(packet)

    while True: #s.connected doesn't exist... hrmm, probably need to catch some error on STOP?
        cmd_type, data = wait_for_sync(s)
        int_cmd = int.from_bytes(cmd_type, 'big')
        print(f'cmd is: {int_cmd}')
        if int_cmd == valid_commands['start']:

            # uint32_t npore = sys_get_be32(packet_data);
            # float Fsample = bytes_to_float((uint8_t*)(&packet_data[0] + 4));
            # create_start_response_packet(1./Fsample, 1, Sscale); // use npore instead of 1 someday
            packet = create_packet('type_info', 2)
            s.sendall(packet)
            i = 0

            file_to_stream = open(filepath_to_stream, 'rb')
            buf_size =  4096*4 # 2*16 #
            data = file_to_stream.read(buf_size)
            while data:
                i += len(data)//2
                packet = create_packet('send_TYPE_PORE_SAMPLES', [i, data])
                #print(packet)
                s.sendall(packet)
                data = file_to_stream.read(buf_size)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("HOST")
    parser.add_argument("PORT", type=int)
    parser.add_argument("-sample_rate_hz", type=float)
    parser.add_argument('-o', '--outfile', nargs='?',
                        type=str,
                        help='output file, in CSV format')
    parser.add_argument('-m', '--masquerade', nargs='?',
                        type=str,
                        help='filepath to BIN for masquerading as a teensy to the webserver')
    args = parser.parse_args()
    # print(args)
    HOST=args.HOST
    PORT=args.PORT
    sample_rate_hz=args.sample_rate_hz
    save_filename = args.outfile

    if args.masquerade:
        # Masquerade mode for local development webserver:
        # python3 teensy_gui/command_line_user_interface.py 192.168.1.14 31416 -m 1b_fromfloat.bin
        masquerade(args.HOST, args.PORT, filepath_to_stream=args.masquerade)
    else:
        command = ''
        while command!='quit':
            command = input('what command do you want to run, options are:'
                            '\n\t{}'.format(valid_commands))
            # command = 'start'
            sub_command = ''
            if command == 'set_pos':
                sub_command = input('provide position (radians)')
            print('constructing packet to send')
            packet = create_packet(command, sub_command)
            if command !='start':
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP uses SOCK_DGRAM
                # s.settimeout(1) #only wait 1 second for a resonse
                s.connect((HOST, PORT))
                print('connected to host')
                s.sendall(packet)
                print('sending packet {}'.format(packet))
                print('waiting on data')
                SYNC = s.recv(1)
                if SYNC and SYNC[0] == sync:
                    print('got good sync')
                    LENGTH_UPPER = s.recv(1)
                    LENGTH_LOWER = s.recv(1)
                    TYPE = s.recv(1)
                    print(SYNC)
                    print(TYPE)
                    print(LENGTH_UPPER)
                    print(LENGTH_LOWER)
                    LENGTH_UPPER = int.from_bytes(LENGTH_UPPER, byteorder='little')
                    LENGTH_LOWER = int.from_bytes(LENGTH_LOWER, byteorder='little')
                    print(f'LENGTH_UPPER {LENGTH_UPPER} LENGTH_LOWER {LENGTH_LOWER}')
                    LENGTH = (LENGTH_UPPER<<8) | LENGTH_LOWER
                    print(f'Received Type {TYPE} and LENGTH {LENGTH}')
                    data = b''
                    if (LENGTH-1):
                        data = s.recv(LENGTH - 1)
                        print(f'Received data: {data}')
                    process_return_data(TYPE, data)
            else:
                q, start_stop_event = threaded_stream(HOST, PORT,
                                                      screen_display_buffer_len=100,
                                                      sample_rate_hz=sample_rate_hz,
                                                      # screen_refresh_rate=0,
                                                      save_filename=save_filename,
                                                      use_fake_data=False)
                while not start_stop_event.is_set():
                    if not q.empty():
                        data = q.get()
                        print(data)
        s.close()