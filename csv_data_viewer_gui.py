#!/usr/bin/python3

""" A GUI to open and view CSV files with format:
sample_num, sample_value

it doesn't open the entire file,
so should easily be able to handle files that are even gigabytes
"""



# for screenshots
# try:
#     from PIL import ImageGrab  # For Windows & OSx
# except:
#     import pyscreenshot as ImageGrab # For Linux

import os
import re
import sys
import time
import tkinter as tk
from threading import Event
from itertools import takewhile, repeat
from datetime import datetime, timedelta

from tkinter import ttk
from tkinter import filedialog
from tkinter.messagebox import showinfo
import os



class App(tk.Frame):
    np_default = 'Num Pulses: {}'
    integral_default = 'Integral: {}'
    take_screenshots = False
    def __init__(self, root, title):
        tk.Frame.__init__(self, root)
        self.pack(expand=True, fill='both')

        self.root = root
        self.data_frame = tk.Frame(self, bg="#dfdfdf")
        self.Line1 = None
        self.stop_event = Event()
        self.results_q = None
        # self.wm_title(title)
        self.root.title(title)
        self.root.minsize(200, 200) 

        self.root.geometry("1024x480")
        self.canvas = tk.Canvas(self.data_frame, background="white")
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.create_line((0, 0, 0, 0), tag='X', fill='darkblue', width=1)
        self.canvas.create_line((0, 0, 0, 0), tag='Y', fill='darkred', width=1)
        self.canvas.create_line((0, 0, 0, 0), tag='Z', fill='darkgreen', width=1)
        self.canvas.pack(side="top", expand=True, fill='both')#, padx=10, pady=10)
        self.scrollbar = tk.Scrollbar(self.data_frame,orient='horizontal')
        self.scrollbar.pack(side="bottom", fill=tk.X)#, expand=True)
        self.scrollbar.config(command=self.scroll_action)
        self.data_frame.pack(side="top", fill="both", expand=True)
        self.config_frame = tk.Frame(self, bg="#dfdfdf")
        

        #self.grid_rowconfigure(0, weight=1)
        #self.grid_columnconfigure(0, weight=1)
        for col_i in range(9):
            #skip allowing resizing on the checkbox and IP address labels
            if col_i in [0, 4,6]:
                continue
            self.config_frame.grid_columnconfigure(col_i, weight=1)
        self.start_b = tk.Button(self.config_frame, text="open file", width=10, command=self.open_csv_popup)
        self.start_b.grid(row=1,column=0)

        tk.Label(self.config_frame, text="Num points shown").grid(row=1, column=1, sticky='w')
        self.numpoints_shown = tk.Entry(self.config_frame)
        self.numpoints_shown.grid(row=2, column=1,sticky="w")
        self.numpoints_shown.insert(0, '512')
        self.numpoints_shown.bind("<Return>", self.refresh_with_larger_screen_buffer)

        tk.Label(self.config_frame, text="Vertical Scaling (1.0 is 100%)").grid(row=1, column=2, sticky='w')
        # self.vertical_scaling = tk.Entry(self.config_frame)
        self.vertical_scaling = tk.Spinbox(self.config_frame, from_=0, to=100, increment=0.01)
        self.vertical_scaling.delete(0,"end")
        self.vertical_scaling.insert(0,1)
        self.vertical_scaling.grid(row=2, column=2,sticky="w")
        self.vertical_scaling.bind("<Return>", self.refresh_with_larger_screen_buffer)
        # self.vertical_scaling.insert(0,'512')

        tk.Label(self.config_frame, text="Vertical Offset (-)").grid(row=1, column=3, sticky='w')
        self.vertical_offset = tk.Spinbox(self.config_frame, from_=-32768, to=32768, increment=1)
        self.vertical_offset.delete(0,"end")
        self.vertical_offset.insert(0,0)
        self.vertical_offset.grid(row=2, column=3,sticky="w")
        self.vertical_offset.bind("<Return>", self.refresh_with_larger_screen_buffer)
        # self.vertical_offset.insert(0,'512')
        # self.vertical_offset.config(state='disabled')

        # tk.Label(self.config_frame, text="Leftmost point").grid(row=1, column=1, sticky='w')
        # self.leftmost_point = tk.Entry(self.config_frame)
        # self.leftmost_point.grid(row=2, column=1,sticky="w")
        # self.leftmost_point.insert(0, '0')

        # tk.Label(self.config_frame, text="Rightmost point").grid(row=1, column=2, sticky='w')
        # self.rightmost_point = tk.Entry(self.config_frame)
        # self.rightmost_point.grid(row=2, column=2,sticky="w")
        # self.rightmost_point.insert(0,'512')

        self.show_labels = tk.IntVar()
        self.show_labels.set(1)
        self.show_labels.checkbox = tk.Checkbutton(self.config_frame, text="Show labels",
                                                   variable=self.show_labels,
                                                   command=self.show_hide_labels)
        self.show_labels.checkbox.grid(row=1, column=4)


        self.config_frame.pack(side="top", fill="x")#, expand=True)

        root.bind('<Left>', self.scroll_left)
        root.bind('<Control-Key-Left>', self.page_left)
        root.bind('<Right>', self.scroll_right)
        root.bind('<Control-Key-Right>', self.page_right)

        self.filename = None
        self.delimeter = None
        self.Y_values = []
        self.loaded_lines = []
        self.num_lines = None
        self.longest_line = '18446744073709551616,-32768\n'
        self.longest_line_len = len(self.longest_line)

        #uncomment during testing to avoid the open CSV popup
        # self.filename = 'output.csv'
        # self.delimeter = ','
        # self.load_file()

    


    def open_csv_popup(self):
        c = CSV_Opener(self)
        self.wait_window(c.win)
        print('DEBUG:', c.delimeter_sv.get(), c.filename)
        self.filename = c.filename
        self.delimeter = c.delimeter_sv.get()
        self.load_file()

    def load_file(self):
        def rawincount(filename):
            # https://stackoverflow.com/a/27518377/253127
            f = open(filename, 'rb')
            bufgen = takewhile(lambda x: x, (f.raw.read(1024*1024) for _ in repeat(None)))
            return sum( buf.count(b'\n') for buf in bufgen )

        self.file_num_bytes = os.stat(self.filename).st_size
        self.num_lines = rawincount(self.filename)
        start_scroll = 0.0
        # self.scroll_window_percentage = self.npoints/self.num_lines
        end_scroll = self.scroll_window_percentage
        if end_scroll>1.0:
            end_scroll = 1.0
        self.scrollbar.set(start_scroll, end_scroll)
        self.file = open(self.filename, 'rb')


        first_line = self.file.readline().decode('utf8')
        import io
        self.file.seek(-(len(self.longest_line)+1), io.SEEK_END)
        last_bytes = self.file.read()
        last_chars = last_bytes.decode('utf8').strip()
        last_line = last_chars.split('\n')[-1]
        first_timestamp = int(first_line.split(self.delimeter)[0])
        last_timestamp =  int(last_line.split(self.delimeter)[0])
        if self.num_lines != (last_timestamp - first_timestamp):
            print(f'WARNING, num_lines ({self.num_lines}) != last_timestamp - first_timestamp ({last_timestamp}  {first_timestamp})')
            tk.messagebox.showerror(title='timestamp error',
                                    message=f'ERROR, num_lines ({self.num_lines}) != (last_timestamp ({last_timestamp}) - first_timestamp ({first_timestamp})) {last_timestamp-first_timestamp})   ')
            self.root.focus_force()


        #import pdb; pdb.set_trace()
        self.file.seek(0, 0)
        self.bytes_position = 0
        self.read_npoints_lines()
        self.plot_data()

    def read_npoints_lines(self):
        self.Y_values = []
        self.loaded_lines = []
        end_n = self.npoints-1
        vis_bytes = 0
        for i, line in enumerate(self.file):
            if line is None:
                break
            vis_bytes += self.move_forward(line)
            if i==(end_n):
                break
        self.visible_buf_num_bytes = vis_bytes

    def read_from_beginning(self):
        self.file.seek(0, 0)
        self.bytes_position = 0
        self.read_npoints_lines()
        self.plot_data()

    def move_forward(self, line):
        line_len = len(line)
        self.bytes_position += line_len
        self.loaded_lines.append(line)
        #try:
        self.Y_values.append(int(line.decode('utf8').split(self.delimeter)[1]))
        # except:
        #     import pdb; pdb.set_trace()
        return line_len

    def show_hide_labels(self, event=None):
        self.canvas.delete("ticks")
        self.refresh_with_larger_screen_buffer()

    def refresh_with_larger_screen_buffer(self, event=None):
        self.bytes_position -= self.visible_buf_num_bytes
        self.file.seek(self.bytes_position, 0)
        self.read_npoints_lines()
        self.on_resize()

    def scroll_right(self, event=None):
        self.file.seek(self.bytes_position, 0)
        line= self.file.readline()
        if line in [b'', '', None]:
            return
        self.Y_values.pop(0)
        first_line = self.loaded_lines.pop(0)
        self.visible_buf_num_bytes -= len(first_line)
        self.visible_buf_num_bytes += self.move_forward(line)
        self.plot_data()

    def scroll_left(self, event=None):
        #import pdb; pdb.set_trace()
        leftmost_byte = self.bytes_position - self.visible_buf_num_bytes
        if leftmost_byte<=0:
            return
        chunk_before_current_visible_buf = leftmost_byte - self.longest_line_len
        if chunk_before_current_visible_buf<0:
            chunk_before_current_visible_buf = 0
        self.Y_values.pop()
        last_line = self.loaded_lines.pop()
        self.bytes_position -= len(last_line)
        self.visible_buf_num_bytes -= len(last_line)
        self.file.seek(chunk_before_current_visible_buf, 0)
        next_bytes = self.file.read(self.longest_line_len)
        next_chars = next_bytes.decode('utf8').strip()
        new_earlier_line = next_chars.split('\n')[-1]
        self.visible_buf_num_bytes += len(new_earlier_line) + 1 # 1 for \n we stripped
        self.loaded_lines.insert(0, new_earlier_line)
        #try:
        self.Y_values.insert(0, int(new_earlier_line.split(self.delimeter)[1]))
        # except:
        #     import pdb; pdb.set_trace()
        self.plot_data()

    def page_right(self, event=None):
        self.file.seek(self.bytes_position, 0)
        self.read_npoints_lines()
        self.plot_data()
        offset_a, offset_b = self.scrollbar.get()
        self.scrollbar.set(offset_b, offset_b+self.scroll_window_percentage)

    def page_left(self, event=None):
        leftmost_byte = self.bytes_position - self.visible_buf_num_bytes
        if leftmost_byte<=0:
            return
        self.bytes_position -= self.visible_buf_num_bytes

        nbytes = self.longest_line_len * self.npoints
        chunk_before_current_visible_buf = leftmost_byte - nbytes
        if chunk_before_current_visible_buf<0:
            self.read_from_beginning()
            return
        self.Y_values = []
        self.loaded_lines = []
        self.file.seek(chunk_before_current_visible_buf, 0)
        next_bytes = self.file.read(nbytes)
        next_chars = next_bytes.decode('utf8').strip()
        loaded_lines = next_chars.split('\n')
        
        self.loaded_lines = loaded_lines[-self.npoints:]
        self.visible_buf_num_bytes = sum([len(line) + 1 for line in self.loaded_lines]) # 1 for \n we stripped
        # self.bytes_position += self.visible_buf_num_bytes
        #try:
        self.Y_values = [int(line.split(self.delimeter)[1]) for line in self.loaded_lines]
        # except IndexError as e:
        #     import pdb; pdb.set_trace()
        #     pass

        self.plot_data()
        offset_a, offset_b = self.scrollbar.get()
        self.scrollbar.set(offset_a-self.scroll_window_percentage, offset_a)


    def scroll_action(self, action, *args):
        if action == "moveto":
            # .0 means that the slider is in its topmost (or leftmost) position, and offset
            #  1.0 means that it is in its bottommost (or rightmost) position
            offset = float(args[0])
            if offset<0:
                data_start_pos, data_end_pos = (0,self.scroll_window_percentage)
                self.read_from_beginning()
            elif offset>1:
                data_start_pos, data_end_pos = (1.0-self.scroll_window_percentage, 1.0)
                # import pdb; pdb.set_trace()
                self.bytes_position = self.file_num_bytes
                self.visible_buf_num_bytes = 0
                self.page_left()
            else:
                data_start_pos, data_end_pos = (offset, offset+self.scroll_window_percentage)
                start_byte = int(data_start_pos*self.file_num_bytes)
                self.file.seek(start_byte, 0)
                buf = self.file.read(self.longest_line_len)
                start_byte += buf.find(b'\n') + 1
                self.file.seek(start_byte, 0)
                self.bytes_position = start_byte
                self.read_npoints_lines()
                self.plot_data()
            self.scrollbar.set(data_start_pos, data_end_pos)
            print(f'scroll_action moveto: offset ({offset}) (range is from 0.0 to 1.0)')
        elif action == 'scroll':
            # size is “-1” or “1” depending on the direction, and the 
            # third argument is “units” to scroll lines (or other unit relevant for the scrolled widget), or “pages” to scroll full pages.
            size = args[0]
            units = args[1]
            print(f'scroll_action scroll: size ({size}) units ({units})')
            if units == 'units':
                if size == '1':
                    self.scroll_right()
                else:
                    self.scroll_left()
            elif units == 'pages':
                if size == '1':
                    self.page_right()
                    # self.scrollbar.set(self.scrollbar.get(), offset+self.scroll_window_percentage)
                else:
                    self.page_left()
                    # self.scrollbar.set(offset-self.scroll_window_percentage, self.scrollbar.get())
        else:
            #print(f'scroll_action unknown: action ({action}) size ({size})', action, size, *args)
            print(f'scroll_action unknown: action ({action}) args:', *args)
            curpos = self.scrollbar.get()
            print(f'curpos {curpos}')
            self.scrollbar.set(0.1,0.2)
        


    @property
    def npoints(self):
        return int(self.numpoints_shown.get())
    # def npoints(self):
    #     return abs(int(self.rightmost_point.get()) - int(self.leftmost_point.get()))
    

    @property
    def scroll_window_percentage(self):
        return self.npoints/self.num_lines
    
    def get_scaling(self):
        x,y,x1,y1 = self.get_widget_bounding_box(self.canvas)
        h = abs(y1-y)
        h_scaling = ((h) / ((2**16))) * float(self.vertical_scaling.get())
        w = abs(x1-x)
        return h,w,h_scaling, int(self.vertical_offset.get())

    def plot_data(self, event=None):
        #print('GUI plot_data')
        # w = self.winfo_width()
        # h = self.winfo_height()
        # h_scaling = h / ((2**16))
        h, w, h_scaling, vertical_offset = self.get_scaling()
        coordsX = []

        # print(f'self.Y_values {len(self.Y_values)}')
        # for n in range(0, self.npoints):
        #     value = self.Y_values[n]
        
        for n, value in enumerate(self.Y_values):
            x = int((w / self.npoints) * n)
            coordsX.append(x)
            y = (int(value * h_scaling) + h//2) - vertical_offset
            coordsX.append(y)

        #print('got frame')
        self.canvas.coords('X', *coordsX)
        # self.before = now

    def on_resize(self, event=None):
        if self.show_labels.get():
            h, w, h_scaling, vert_off = self.get_scaling()
            # min_y = (int(-32768 * h_scaling) + h//2) - vert_off
            # max_y = (int(32768 * h_scaling) + h//2) - vert_off
            self.canvas.delete("ticks")
            num_h_ticks = w//50 # 50 pixels minimum distance between on-screen ticks
            for n in range(0, self.npoints, self.npoints//num_h_ticks):
                x = int((w / self.npoints) * n)
                self.canvas.create_line(x,0,x,5, width=2, tag='ticks')
                self.canvas.create_text(x,0, text='%d'% (n), anchor=tk.N, tag='ticks')
            # for n, value in enumerate(self.Y_values):
            #     if n%50==0:
            #         x = int((w / self.npoints) * n)
            #         #x = 0 + (n)
            #         self.canvas.create_line(x,0,x,5, width=2, tag='ticks')
            #         self.canvas.create_text(x,0, text='%d'% (n), anchor=tk.N, tag='ticks')

            print(vert_off)
            # for y in range(min_y, max_y, 50):
            vert_tick_dist = h//10
            num_ticks = h//50
            print(f'num_ticks {num_ticks}')
            #for y in range(0, h, h//10):
            for y in range(-32768, 32768, (2**16)//16):
                #scaled_y = ((y+32768)*h_scaling)+vert_off
                scaled_y = (int(y * h_scaling) + h//2) - vert_off
                #print(h, y, scaled_y, h_scaling)
                # y = (int(pix * h_scaling) + h//2) - vert_off
                # self.canvas.create_line(0, y, 5, y, width=2, tag='ticks')
                #self.canvas.create_text(0, y, text=' %d'% (((y/h_scaling)-32768)+vert_off), anchor=tk.W, tag='ticks')
                self.canvas.create_text(0, scaled_y, text=' %d'% y, anchor=tk.W, tag='ticks')
        self.plot_data()
    
    # def screenshot(self):
    #     if self.take_screenshots:
    #         pulse_date = datetime.now().strftime('%m_%d_%Y__%H_%M_%S')
    #         ImageGrab.grab(bbox=canvas).save("out_snapsave.jpg")
    #         self.get_widget_bounding_box(self.canvas)
    #         waveform_filename = os.path.join(self.output_directory, 'waveform_{}__{}.png'.format(pulse_date, self.pulse_setting_string))
    #         ImageGrab.grab(bbox=canvas).save(waveform_filename)
    #         #ImageGrab.grab().crop((x,y,x1,y1)).save("file path here")

    def get_widget_bounding_box(self, widget):
        x=widget.winfo_rootx()+widget.winfo_x()
        y=widget.winfo_rooty()+widget.winfo_y()
        x1=x+widget.winfo_width()
        y1=y+widget.winfo_height()
        box=(x,y,x1,y1)
        return box


class CSV_Opener(object):
    def __init__(self, parent):
        win = tk.Toplevel(parent)
        self.win = win
        win.wm_title("Open CSV File")
        win.focus()

        tk.Label(win, text="CSV delimeter").grid(row=0, column=0, sticky='w')
        self.delimeter_sv = tk.StringVar()
        delimeter = tk.Entry(win, textvariable=self.delimeter_sv)
        delimeter.grid(row=0, column=1,sticky="w")
        delimeter.insert(0,',')

        l = tk.Button(win, text="Open file", command=self.opn)
        l.grid(row=1, column=0)

        tk.Label(win, text="Raw CSV lines").grid(row=2, column=0, sticky='w')
        self.listbox = tk.Listbox(win)
        self.listbox.grid(row=3, column=0)
        tk.Label(win, text="Parsed CSV lines (X, Y)").grid(row=2, column=1, sticky='we', columnspan=2)
        self.parsed_listbox_x = tk.Listbox(win)
        self.parsed_listbox_x.grid(row=3, column=1)
        self.parsed_listbox_y = tk.Listbox(win)
        self.parsed_listbox_y.grid(row=3, column=2)
        
        b = tk.Button(win, text="Done", command=win.destroy)
        b.grid(row=4, column=0)
        
        self.delimeter_sv.trace_add("write", self.callback)
        self.filename = None

    def callback(self, *args):
        self.update_parsed_list()

    def opn(self):
        self.filename = filedialog.askopenfilename(initialdir=os.getcwd(), title="Select file", filetypes=(("CSV files","*.csv"),("all files","*.*")))
        with open(self.filename) as f:
            for i, line in enumerate(f):
                print(line)
                self.listbox.insert(tk.END, line.strip())
                if i==4:
                    break
        self.update_parsed_list()

    def update_parsed_list(self):
        self.parsed_listbox_x.delete(0,tk.END)
        self.parsed_listbox_y.delete(0,tk.END)
        for i, listbox_entry in enumerate(self.listbox.get(0, tk.END)):
            x,y = listbox_entry.split(self.delimeter_sv.get())
            self.parsed_listbox_x.insert(tk.END, x)
            self.parsed_listbox_y.insert(tk.END, y)


def main(args = None):
    if args is None:
        args = sys.argv

    if len(args) == 1:
        root = tk.Tk()
        app = App(root, "Demonpore CSV DataViewer!")
        root.mainloop()
        return 0
    else:
        print('usage: data_viewer.py')
        return -1


if __name__ == '__main__':
    sys.exit(main())
