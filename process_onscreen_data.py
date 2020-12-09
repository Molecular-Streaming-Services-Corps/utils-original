import os, sys
from importlib import reload
pth = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','signals'))
sys.path.insert(0, pth)
import stats
reload(stats)


def run(self):
    print('current Y values on screen')
    for y in self.Y_values:
        print(y)
    # print("\n\nlines:")
    # for line in self.loaded_lines:
    #   print(line)
    
    # sd = stats.standard_deviation(self.Y_values)
    # rms = stats.rms(self.Y_values)
    # print(f'std_dev {sd} and RMS: {rms}')
    print(f'\nbyte num at right of screen: {self.bytes_position}')
    spikes, sd, rms = stats.get_spikes(self.Y_values,
                                           exceptional_peak_sd=5.0,
                                           peak_side_sd=1.5)
    self.canvas.delete("clicks")
    self.canvas.delete("spikes")
    h, w, h_scaling, vertical_offset = self.get_scaling()
    for spike_num, spike in enumerate(spikes):
        for n,v in spike:
            x = int((w / self.npoints) * n)
            #y = (int((v+vertical_offset) * h_scaling) + h//2)
            y = (int((v + vertical_offset) * h_scaling) + h//2)
            y = h - y # invert the Y axis so the origin is at bottom of screen
            print(f'n {n}, v {v}, x {x}, y {y}')
            x1, y1 = (x - 1), (y - 1)
            x2, y2 = (x + 1), (y + 1)
            self.canvas.create_oval(x1, y1, x2, y2, fill="yellow", outline='red', tags='spikes')#476042")

        spike_width, spike_height = stats.get_spike_width_height(spike)
        print(f'spike group {spike_num} has width {spike_width} and height {spike_height}')
    _max = max(self.Y_values)
    _min = min(self.Y_values)
    avg = sum(self.Y_values)/len(self.Y_values)
    print(f'rms {rms} sd {sd}\n'
          f'mix Y vals {_min} max  {_max} max-min  {_max-_min}\n'
          f'max-rms {abs(_max)-abs(rms)}\n'
          f'min-rms {abs(_min)-abs(rms)}\n'
          f'(max-rms)/std_dev = {(abs(_max)-abs(rms))/sd}\n'
          f'(min-rms)/std_dev = {(abs(_min)-abs(rms))/sd}\n'
          f'avg {avg} #points {len(self.Y_values)}')
    # 16.716000
    # 17.566795