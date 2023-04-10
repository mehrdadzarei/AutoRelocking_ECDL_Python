######################################################################################################
# @author Mehrdad Zarei <mzarei@umk.pl>
# @date 2023.03.28
# @version 0
#
# @brief re-locking lasers
#
######################################################################################################



import sys, time
from inputimeout import inputimeout
from datetime import datetime
import json
import threading
import socket
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import wavelength_meter
from wlmConst import *
# import laser_control



class AutoRelocking:

    def __init__(self):

        with open('setting.json') as json_file:
            data = json.load(json_file)
        
        self.general = data['general'][0]
        self.path = self.general['path']

        # self.wlm = wavelength_meter.WavelengthMeter(dllpath = self.general['dllpath'], WlmVer = int(self.general['WlmVer']))
        # self.lc = laser_control.LaserControl()
        
        # [name, target frequency, PiezoRelockMode, CurrentRelockMode, update, portNamePiezo, portNameCurrent, portNameInput]
        self.chName = data['chName'][1]
        # [no peaks diff, freq_diff_thr, freq_diff_std, has_refData]
        self.refDataInfo = data['refDataInfo'][1]
        self.fname = {'1': self.path + 'refCh1.txt', '2': self.path + 'refCh2.txt', '3': self.path + 'refCh3.txt', '4': self.path + 'refCh4.txt',\
                       '5': self.path + 'refCh5.txt', '6': self.path + 'refCh6.txt', '7': self.path + 'refCh7.txt', '8': self.path + 'refCh8.txt'}
        # [min, max, last_value, prev_state]
        self.IParam = data['IParam'][1]
        # [min, max, last_value, prev_state]
        self.PztParam = data['PztParam'][1]
        
        self.currStep = 0.001       # v, it depends to reseloution 
        self.piezo_step = 0.001     # v, it depends to reseloution 
        self.piezo_delay = 0.002    # delay s to apply new value for piezo
        self.diff_piezo_drift = 1.0
        self.diff_t_drift = 0
        self.freq_diff = 0.0
        self.record = 0.0
        self.noPeaks_diff = 0
        self.height_thr = 150
        self.distance_thr = 20
        self.noP_diff_thr = 8
        self.noP_diff_std = 7
        # self.freq_diff_thr = 0.0001
        # self.freq_diff_std = 0.00005
        self.relock = {'1': {'time': [], 'freq': [], 'trans': []},
                       '2': {'time': [], 'freq': [], 'trans': []},
                       '3': {'time': [], 'freq': [], 'trans': []},
                       '4': {'time': [], 'freq': [], 'trans': []},
                       '5': {'time': [], 'freq': [], 'trans': []},
                       '6': {'time': [], 'freq': [], 'trans': []},
                       '7': {'time': [], 'freq': [], 'trans': []},
                       '8': {'time': [], 'freq': [], 'trans': []}}
        self.relock_event = {'1': {'time': [], 'long': []},
                             '2': {'time': [], 'long': []},
                             '3': {'time': [], 'long': []},
                             '4': {'time': [], 'long': []},
                             '5': {'time': [], 'long': []},
                             '6': {'time': [], 'long': []},
                             '7': {'time': [], 'long': []},
                             '8': {'time': [], 'long': []}}
        self.daych = 0
        self.save_data()
        self.no_rel = 0
        self.trans = 1

        # self.wlm.run(action = 'show')    # show or hide
        # self.wlm.measurement(cCtrlStartMeasurement)   # state : cCtrlStopAll, cCtrlStartMeasurement

    def close (self):

        data = {'general': [self.general], 
                'chName' : [{'description':'[name, target frequency, PiezoRelockMode (0 or 1), CurrentRelockMode (0 or 1), update (0 or 1), portNamePiezo, portNameCurrent, portNameInput]'},
                            self.chName],
                'IParam' : [{'description':'[min, max, last_value, prev_state (+ or -)]'}, self.IParam], 
                'PztParam' : [{'description':'[min, max, last_value, piezo_drift0, piezo_drift1, t_drift0, t_drift1, drift_no]'}, self.PztParam],
                'refDataInfo' : [{'description':'[no peaks diff, freq_diff_thr, freq_diff_std, has_refData (0 or 1)]'}, self.refDataInfo]}

        # indent is used to be readable by human but will increase the size of file and is not recomended for transfering data
        json_string = json.dumps(data, indent=4)

        # print(json_string)
        # with open('setting.json', 'w') as outfile:
        #     outfile.write(json_string)
        # print("done")

        self.save_data()

    def save_data(self):

        if datetime.today().day != self.daych:

            self.daych = datetime.today().day
            headerch = True
        else:
            headerch = False

        t = datetime.now()
        
        for i in self.chName:

            if self.chName[i][2] == 1 or self.chName[i][3] == 1:
        
                relock_data = pd.DataFrame(data=self.relock[i])
                relock_data_event = pd.DataFrame(data=self.relock_event[i])

                name1 = i + '_relock_data_' + t.strftime('%m_%d_%Y') + '.csv'
                name2 = i + '_relock_data_event_' + t.strftime('%m_%d_%Y') + '.csv'
                relock_data.to_csv(name1, index=False, mode='a', header=headerch)
                relock_data_event.to_csv(name2, index=False, mode='a', header=headerch)
        
        self.relock = {'1': {'time': [], 'freq': [], 'trans': []},
                       '2': {'time': [], 'freq': [], 'trans': []},
                       '3': {'time': [], 'freq': [], 'trans': []},
                       '4': {'time': [], 'freq': [], 'trans': []},
                       '5': {'time': [], 'freq': [], 'trans': []},
                       '6': {'time': [], 'freq': [], 'trans': []},
                       '7': {'time': [], 'freq': [], 'trans': []},
                       '8': {'time': [], 'freq': [], 'trans': []}}
        self.relock_event = {'1': {'time': [], 'long': []},
                             '2': {'time': [], 'long': []},
                             '3': {'time': [], 'long': []},
                             '4': {'time': [], 'long': []},
                             '5': {'time': [], 'long': []},
                             '6': {'time': [], 'long': []},
                             '7': {'time': [], 'long': []},
                             '8': {'time': [], 'long': []}}
    
    def setReference(self):

        for i in self.refDataInfo:
            if self.chName[i][3] == 1:
                try:
                    with open(self.fname[i], 'r') as f:

                        refData = []
                        for line in f.readlines():

                            refData.append(float(line))
                        f.close()

                        self.refDataInfo[i][3] = 1
                        peaksIndRef, peaksHRef = find_peaks(refData, height = self.height_thr, distance = self.distance_thr)
                        self.refDataInfo[i][0] = len(peaksIndRef)
                except IOError:
                    continue
    
    def getInfo(self, ch):

        self.wlm.setSwitcherChannel(ch)

        self.freqCh = self.wlm.getFrequency(ch)
        if self.freqCh == -4:
            
            self.wlm.setExposureMode(ch, True)
            time.sleep(0.1)
            self.wlm.setExposureMode(ch, False)
            self.freqCh = self.wlm.getFrequency(ch)

        diff = abs(float(self.chName[str(ch)][1]) - self.freqCh)
        if diff < 50:
            
            self.freq_diff = diff
            self.record = float(self.chName[str(ch)][1]) - self.freqCh
            if self.refDataInfo[str(ch)][3] == 1:

                spec = self.wlm.spectrum(ch)
                peaksIndSpec, peaksHSpec = find_peaks(spec, height = self.height_thr, distance = self.distance_thr)
                self.noPeaksSpec = len(peaksIndSpec)
                self.noPeaks_diff = abs(self.noPeaksSpec - self.refDataInfo[str(ch)][0])
        else:
            self.freq_diff = -1
            self.noPeaks_diff = -1

        if self.chName['7'][2] == 1:

            val = self.lc.getInput(self.chName[str(ch)][7], 100)
            self.trans = np.average(val)
        
        self.relock[str(ch)]['freq'].append(self.record)
        self.relock[str(ch)]['time'].append(time.time())
        self.relock[str(ch)]['trans'].append(self.trans)
        # self.freq_list.append(self.freqCh)
        # self.time_list.append(time.ctime())
    
    def scanning(self, per = 0.2, ch = 1):

        # if per = 2.0, whole range will be scan and it is good to find target frequency
        piezo_max = self.PztParam[str(ch)][1]
        piezo_min = self.PztParam[str(ch)][0]
        piezo_last_value = self.PztParam[str(ch)][2]
        scan_range = (piezo_max - piezo_min) * per / 2
        min_scan = piezo_last_value - scan_range
        if min_scan <= piezo_min:
            min_scan = piezo_min
        max_scan = piezo_last_value + scan_range
        if max_scan >= piezo_max:
            max_scan = piezo_max
        len_right_scan = np.floor((max_scan - piezo_last_value) / self.piezo_step)
        len_scan = np.floor((max_scan - min_scan) * 2 / self.piezo_step)
        curr_val = 0.0
        prev_freq_diff = self.freq_diff
        std_freq = self.refDataInfo[str(ch)][1] - self.refDataInfo[str(ch)][2]
        i = 0

        # check direction base on laser drift, if negative change direction
        if self.diff_piezo_drift < 0:
            i = len_right_scan
            max_scan = piezo_last_value

        while i < len_scan:

            if self.freq_diff < std_freq and self.trans > 0.5:
                
                self.PztParam[str(ch)][2] = curr_val
                return 2        # to start scaning in small range
            
            if self.freq_diff < std_freq * 2 and per == 0.4:    # very good condition
                
                self.PztParam[str(ch)][2] = curr_val
                return 2
            elif self.freq_diff < std_freq * 4 and per == 0.8:    # good condition
                
                return 3
            elif self.freq_diff < std_freq * 6 and per == 2.0:    # bad condition
                
                return 4
            
            if i < len_right_scan:
            
                curr_val = piezo_last_value + i * self.piezo_step
                if curr_val >= piezo_max:
                    curr_val = piezo_max

                # check direction base on freq
                if self.freq_diff > (prev_freq_diff + (std_freq * 10)):

                    i = len_right_scan
                    max_scan = curr_val
                    prev_freq_diff = self.freq_diff
                    continue
                if i == (len_right_scan - 1) or curr_val == piezo_max or curr_val > max_scan:

                    i = len_right_scan - 1
                    prev_freq_diff = self.freq_diff
            elif i < (len_right_scan + (len_scan / 2)):
                
                curr_val = max_scan + (len_right_scan - i) * self.piezo_step
                if curr_val <= piezo_min:
                    curr_val = piezo_min

                # check direction base on freq
                if self.freq_diff > (prev_freq_diff + (std_freq * 10)):

                    i = (len_right_scan + (len_scan / 2))
                    min_scan = curr_val
                    prev_freq_diff = self.freq_diff
                    continue
                if curr_val == piezo_min or curr_val < min_scan:
                    i = (len_right_scan + (len_scan / 2)) - 1
            else:

                curr_val = min_scan + (i - (len_right_scan + (len_scan / 2))) * self.piezo_step
                if curr_val >= piezo_max:
                    curr_val = piezo_max

                if curr_val == piezo_max or curr_val > max_scan:
                    i = len_scan
            
            # print(curr_val)
            self.lc.setOutput(self.chName[str(ch)][5], curr_val)
            time.sleep(0.01)
            self.getInfo(ch)
            i += 1

        return 1
    
    def piezo_scan(self, ch):

        repeat = 1
        rng_scan = 1
        no_scan = 0
        max_no_scan = 5
        t1 = time.time()    # to keep for saving data

        while repeat > 0:

            if self.freq_diff < (self.refDataInfo[str(ch)][1] - self.refDataInfo[str(ch)][2]) \
                and self.trans > 0.5:
                break

            # if is not able to find the Mode, stop searching
            if no_scan == max_no_scan:
                repeat = 0
                break

            if rng_scan == 1:

                self.piezo_delay = 0.02     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.2, ch)
                rng_scan = 2
            elif rng_scan == 2:

                self.piezo_delay = 0.015     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.4, ch)
                rng_scan = 3
            elif rng_scan == 3:

                self.diff_piezo_drift = 1;       # after this case don't care about direction
                self.piezo_delay = 0.01     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.8, ch)
                rng_scan = 4
            elif rng_scan == 4:

                self.piezo_delay = 0.005     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(2.0, ch)
                rng_scan = 1
                no_scan += 1

            if repeat == 2:

                rng_scan = 1
                repeat = 1
                no_scan = 0
                time.sleep(1)
            elif repeat == 3:

                rng_scan = 2
                repeat = 1
                no_scan = 0
            elif repeat == 4:

                rng_scan = 3
                repeat = 1
                no_scan = 0

        # duration from lock to unlock
        self.diff_t_drift = t1 - self.PztParam[str(ch)][6]
        # drift from last lock to new lock
        self.diff_piezo_drift = self.PztParam[str(ch)][2] - self.PztParam[str(ch)][4]
        # save new data only if last lock survive for more than of 30 s and laser drift is more than of 10 mv
        if self.diff_t_drift > 30 and abs(self.diff_piezo_drift) > (self.piezo_step * 10):

            self.PztParam[str(ch)][5] = self.PztParam[str(ch)][6]               # previous time value on lock
            self.PztParam[str(ch)][6] = time.time()                             # new value on lock
            self.PztParam[str(ch)][3] = self.PztParam[str(ch)][4]               # previous drift value on lock
            self.PztParam[str(ch)][4] = self.PztParam[str(ch)][2]               # new drift value on lock
            if self.PztParam[str(ch)][7] < 10:                                  # to avoide raising to much of drift_no
                self.PztParam[str(ch)][7] += 1
        else:
            self.diff_piezo_drift = self.PztParam[str(ch)][4] - self.PztParam[str(ch)][3]   # we need to keep the previous laser drift for drifting
    
    def locking(self, ch):

        self.iCurrVal = self.IParam[str(ch)][2]
        self.pztCurrVal = self.PztParam[str(ch)][2]
        # scan_range = 30

        if self.chName[str(ch)][2] == 1:

            self.lc.setOutput(self.chName[str(ch)][5], self.pztCurrVal)
            self.pztState = True
        else:
            self.pztState = False

        if self.chName[str(ch)][3] == 1:

            self.lc.setOutput(self.chName[str(ch)][6], self.iCurrVal)
            self.currState = True
        else:
            self.currState = False

        time.sleep(0.01)
        self.getInfo(ch)

        # if self.currState:

        #     if (self.freq_diff > self.freqStep or self.noPeaks_diff > self.noP_diff_thr):
            
        #         scan_range = self.current_scan(scan_range)
        #     else:
        #         self.currState = False

        # if (self.freq_diff > self.freqStep or self.noPeaks_diff > self.noP_diff_thr):

        #     self.chName[str(ch)][3] = 0

        if self.pztState and (self.freq_diff >= self.refDataInfo[str(ch)][1] or (self.trans < 0.5 and self.trans > -1)):
            
            # drift_no 
            if self.PztParam[str(ch)][7] >= 2:

                # new - prevoius, laser drift
                self.diff_piezo_drift = self.PztParam[str(ch)][4] - self.PztParam[str(ch)][3]
                # to avoid large numbers in laser drift
                if abs(self.diff_piezo_drift) < self.piezo_step:
                    self.diff_piezo_drift = (self.diff_piezo_drift / abs(self.diff_piezo_drift)) * self.piezo_step

                # stop - start, is duration of keeping lock
                self.diff_t_drift = self.PztParam[str(ch)][6] - self.PztParam[str(ch)][5]
            else:

                # positive direction
                self.diff_piezo_drift = 1
                self.diff_t_drift = 1

            t0 = time.time()
            self.relock_event[str(ch)]['time'].append(t0)
            self.piezo_scan(ch)
            self.relock_event[str(ch)]['long'].append((time.time() - t0))
        # else:
        #     self.pztState = False
    
    # def cavityCheck(self, ch):

    #     val = self.lc.getInput(self.chName[str(ch)][7], 100)
    #     self.trans = np.average(val)
    #     self.relock['trans'].append(self.trans)
        
    #     if self.trans < 0.5 and self.trans > -1:
    #         self.locking(ch)
    
    def analyse(self):

        for i in self.chName:

            if self.chName[i][2] == 1 or self.chName[i][3] == 1:

                self.getInfo(int(i))
                print(self.chName[i][0] + ' ' + str(self.freqCh))

                # if self.chName['7'][2] == 1:
                #     self.cavityCheck(int(i))

                if self.freq_diff >= self.refDataInfo[i][1] or self.noPeaks_diff > self.noP_diff_thr \
                    or (self.trans < 0.5 and self.trans > -1):
                    
                    self.no_rel += 1
                    print('start relocking... ', self.no_rel, ' times', ' at ', time.ctime())
                    self.locking(int(i))

    def update(self):

        t0 = time.time()
        
        while True:

            # save data every x s
            if (time.time() - t0) >= 60:

                self.save_data()
                t0 = time.time()

            # self.analyse()

            # time.sleep(5)
            try:
                time_over = inputimeout(prompt='End (y/n): ', timeout=5)
                if time_over == "y":
                    break
                else:
                    print('\033[A', end="")
            except Exception:
                print('\033[A', end="")


if __name__ == '__main__':

    app = AutoRelocking()
    # app.setReference()

    app.update()

    app.close()


