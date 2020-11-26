# utils
miscellaneous utility stuff

# Requirements
**Python3**

pip install pandas numpy


# Offline Data Viewer GUI (CSV and Binary files)

Assumes you have the **utils** and **signals** repos cloned in adjacent directories, example:
 * Projects
   * signals
     * stats.py
   * utils
     * offline_data_viewer_gui.py

## Instructions
### Open a CSV
You can use the GUI and the open button, or you can use the command-line to directly open a file:
 * python3 offline_data_viewer_gui.py --csv ../experiments/1B_blood_floats.csv

### Open a Binary file (demonpore custom electronics)
The binary file format is simple today, just a stream of packed **int16** values (-32768 to 32768)
 * python3 offline_data_viewer_gui.py --bin ../experiments/test.bin

## GUI navigation
 * **CTRL + RIGHT** (arrow key) -- scroll right one **screen** (i.e. page) at a time
 * **CTRL + LEFT**  (arrow key) -- scroll left  one **screen** (i.e. page) at a time
 * **RIGHT**  (arrow key) -- scroll right one **value** at a time
 * **LEFT**   (arrow key) -- scroll left  one **value** at a time
  * currently has a bug where the data doesn't load correctly, simply scroll right or page left/right to reset things
 * **Click data** -- prints the (X,Y) coordinates and some other debug info on the terminal
 * **Click 'Find Peaks on-screen'**
   * reloads **process_onscreen_data.py** then passes the visible on-screen data to the **run** function inside there
   * **run** then runs the peak finding algorithm found in **stats.py** (from the **signals** repo)
   * any detected peak-group points are then drawn on-screen in orange
