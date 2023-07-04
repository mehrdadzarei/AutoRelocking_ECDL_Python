######################################################################################################
# @author Mehrdad Zarei <mzarei@umk.pl>
# @date 2023.03.28
# @version 0
#
# @brief re-locking lasers
#
######################################################################################################



import os, time
from inputimeout import inputimeout
from datetime import datetime
import json
import threading
import socket
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import Client
# from wlmConst import *
import laser_control



class AutoRelocking:

    def __init__(self):

        with open('setting.json') as json_file:
            data = json.load(json_file)
        
        self.general = data['general'][0]
        self.path = self.general['path']

        self.lc = laser_control.LaserControl()
        
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
        
        self.freqCh = 0.0
        self.freqStep = 0.001       # 1 GHz
        self.curr_step = 0.001      # v, it depends to reseloution 
        self.piezo_step = 0.001     # v, it depends to reseloution 
        self.piezo_delay = 0.002    # delay s to apply new value for piezo
        self.curr_delay = 0.002     # delay s to apply new value for current
        self.diff_cur_drift = 1.0
        self.diff_piezo_drift = 1.0
        self.diff_t_drift = 0
        self.freq_diff = 0.0
        self.tranLevel = 0.3
        self.record = 0.0
        self.noPeaks_diff = 0
        self.height_thr = 100
        self.distance_thr = 20
        self.noP_diff_thr = 6
        self.noP_diff_std = 4
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
        self.transList = {'1': 1, '2': 1, '3': 1, '4': 1, '5': 1, '6': 1, '7': 1, '8': 1}
        self.monitoring = False
        self.relocking = False
        self.relockingCavity = False
        self.relockingCh = '1'
        self.communicating = False

        connected = False
        for i in self.chName:

            if not connected and self.chName[i][9] == 1:

                self.wlm = Client.wlmClient(time_out=60)
                self.wlm.connect(ip = self.general['IP'], port = self.general['PORT'])
                self.wlm.setPrec(self.general['WLMPrec'])

                connected = True
            
            # set drift number on 0
            self.PztParam[i][7] = 0
            # set first drift time on 60
            self.PztParam[i][9] = 60

    def close (self):

        try:
            self.save_data()
            self.wlm.disconnect()
        except Exception:
            pass

    def save_data(self):

        # if datetime.today().day != self.daych:

        #     self.daych = datetime.today().day
        #     headerch = True
        # else:
        #     headerch = False

        data = {'general': [self.general], 
                'chName' : [{'description':'[name, target frequency, PiezoRelockMode (0 or 1), CurrentRelockMode (0 or 1), update (0 or 1), portNamePiezo, portNameCurrent, portNameInput, cavityLock, wavemeterLock, laserDrift]'},
                            self.chName],
                'IParam' : [{'description':'[min, max, last_value, cur_drift0, cur_drift1, drift_no]'}, self.IParam], 
                'PztParam' : [{'description':'[min, max, last_value, piezo_drift0, piezo_drift1, t_drift0, t_drift1, drift_no, t1Drift, firstDrift_t]'}, self.PztParam],
                'refDataInfo' : [{'description':'[no peaks diff, freq_diff_thr, freq_diff_std]'}, self.refDataInfo]}

        # indent is used to be readable by human but will increase the size of file and is not recomended for transfering data
        json_string = json.dumps(data, indent=4)

        # print(json_string)
        with open('setting.json', 'w') as outfile:
            outfile.write(json_string)
        # print("done")

        t = datetime.now()
        
        for i in self.chName:

            if self.chName[i][2] == 1 or self.chName[i][3] == 1:
        
                relock_data = pd.DataFrame(data=self.relock[i])
                relock_data_event = pd.DataFrame(data=self.relock_event[i])
            
                name1 = 'data/' + i + '_relock_data_' + t.strftime('%m_%d_%Y') + '.csv'
                name2 = 'data/' + i + '_relock_data_event_' + t.strftime('%m_%d_%Y') + '.csv'
                if os.path.isfile(name1) or os.path.isfile(name2):
                    headerch = False
                else:
                    headerch = True
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
                
                if self.refDataInfo[i][0] == 0:

                    self.getInfo(int(i))
                    self.refDataInfo[i][0] = self.noPeaksSpec
    
    def monitor_cavity(self, event):

        while self.monitoring:

            # if it is not on locking process go inside
            if not self.relocking:
                for i in self.chName:
                    if self.chName[i][8] == 1 and (self.chName[i][2] == 1 or self.chName[i][3] == 1):

                        val = self.lc.getInput(self.chName[i][7], 100)
                        self.transList[i] = np.average(val)

                        if (self.transList[i] < self.tranLevel and self.transList[i] > -1):

                            # print(self.transList[i])
                            # wait till other locking is done
                            while self.relocking:
                                time.sleep(0.1)
                            
                            self.relockingCh = i
                            self.relockingCavity = True
                            # self.relocking = True
                            # self.no_rel += 1
                            # print('start relocking... ', self.no_rel, ' times', ' at ', time.ctime())
                            # # start thread for locking
                            # locking_thread = threading.Thread(target=self.locking, args=(i))
                            # locking_thread.start()
                            break
                            # self.locking(int(i))

            # check for stop
            if event.is_set():
                break
            time.sleep(1)
    
    def getInfo(self, ch):

        # wait till other communication is done
        while self.communicating:
            time.sleep(0.01)
        self.communicating = True

        # getting wavemetere info
        if self.chName[str(ch)][9] == 1:

            try:
                self.freqCh = float(self.wlm.getFrequency(ch))
            
                if self.freqCh == -31:

                    # try to reconnect again
                    try:
                        # check if connection is not closed
                        try:
                            print("[ERROR -31]")
                            self.wlm.disconnect()
                            time.sleep(0.5)
                        except Exception:
                            pass
                        self.wlm = Client.wlmClient(time_out=60)
                        self.wlm.connect(ip = self.general['IP'], port = self.general['PORT'])
                        self.wlm.setPrec(self.general['WLMPrec'])
                        self.freqCh = float(self.wlm.getFrequency(ch))
                    except Exception as e:
                        # print(f"[ERROR] {e}")
                        pass

                if self.freqCh == -3 or self.freqCh == -4:
                    
                    self.wlm.setExpoAuto(1)
                    time.sleep(0.1)
                    self.wlm.setExpoAuto(0)
                    self.freqCh = float(self.wlm.getFrequency(ch))
            except Exception:
                pass

            diff = abs(float(self.chName[str(ch)][1]) - self.freqCh)
            if diff < 50:
                
                self.freq_diff = diff
                self.record = float(self.chName[str(ch)][1]) - self.freqCh
                if self.chName[str(ch)][3] == 1:

                    spec = self.wlm.getSpectrum(ch)
                    try:
                        peaksIndSpec, peaksHSpec = find_peaks(spec, height = self.height_thr, distance = self.distance_thr)
                        self.noPeaksSpec = len(peaksIndSpec)
                    except Exception:
                        pass
                    self.noPeaks_diff = abs(self.noPeaksSpec - self.refDataInfo[str(ch)][0])
                    # print(self.noPeaks_diff)
            else:
                self.freq_diff = -1
                self.noPeaks_diff = -1

        # getting cavity info
        if self.chName[str(ch)][8] == 1:

            if self.relocking:

                val = self.lc.getInput(self.chName[str(ch)][7], 100)
                self.trans = np.average(val)
            else:
                self.trans = self.transList[str(ch)]
        
        self.relock[str(ch)]['freq'].append(self.record)
        self.relock[str(ch)]['time'].append(time.time())
        self.relock[str(ch)]['trans'].append(self.trans)
        # self.freq_list.append(self.freqCh)
        # self.time_list.append(time.ctime())

        self.communicating = False

    def scanningCur(self, per = 0.2, ch = 1):

        # if per = 2.0, whole range will be scan and it is good to find target frequency
        curr_max = self.IParam[str(ch)][1]
        curr_min = self.IParam[str(ch)][0]
        curr_last_value = self.IParam[str(ch)][2]
        scan_range = (curr_max - curr_min) * per / 2
        min_scan = curr_last_value - scan_range
        if min_scan <= curr_min:
            min_scan = curr_min
        max_scan = curr_last_value + scan_range
        if max_scan >= curr_max:
            max_scan = curr_max
        len_right_scan = np.floor((max_scan - curr_last_value) / self.curr_step)
        len_scan = np.floor((max_scan - min_scan) * 2 / self.curr_step)
        curr_val = 0.0
        i = 0

        # check direction base on laser drift, if negative change direction
        if self.diff_cur_drift < 0:
            i = len_right_scan
            max_scan = curr_last_value

        while i < len_scan:

            if self.freq_diff < self.freqStep and self.noPeaks_diff < (self.noP_diff_thr - self.noP_diff_std):
                
                self.IParam[str(ch)][2] = curr_val
                return 2        # to start scaning in small range
            
            if i < len_right_scan:
            
                curr_val = curr_last_value + i * self.curr_step
                if curr_val >= curr_max:
                    curr_val = curr_max

                if i == (len_right_scan - 1) or curr_val == curr_max or curr_val > max_scan:

                    i = len_right_scan - 1
            elif i < (len_right_scan + (len_scan / 2)):
                
                curr_val = max_scan + (len_right_scan - i) * self.curr_step
                if curr_val <= curr_min:
                    curr_val = curr_min

                if curr_val == curr_min or curr_val < min_scan:
                    i = (len_right_scan + (len_scan / 2)) - 1
            else:

                curr_val = min_scan + (i - (len_right_scan + (len_scan / 2))) * self.curr_step
                if curr_val >= curr_max:
                    curr_val = curr_max

                if curr_val == curr_max or curr_val > max_scan:
                    i = len_scan
            
            # print(curr_val)
            self.lc.setOutput(self.chName[str(ch)][6], curr_val)
            time.sleep(0.01)
            if not self.relocking:
                break
            self.getInfo(ch)
            i += 1

        return 1
    
    def current_scan(self, ch):

        repeat = 1
        rng_scan = 1
        no_scan = 0
        max_no_scan = 5

        while self.relocking and repeat > 0:

            if self.freq_diff < self.freqStep and self.noPeaks_diff < (self.noP_diff_thr - self.noP_diff_std):
                break

            # if is not able to find the Mode, stop searching
            if no_scan == max_no_scan:
                
                repeat = 0
                self.chName[str(ch)][3] = 0
                print("[NOT FOUND] Single Mode is not in the range of scan")
                break

            if rng_scan == 1:

                self.curr_delay = 0.01     # s
                self.curr_step = 1 * self.curr_step
                repeat = self.scanningCur(0.05, ch)
                rng_scan = 2
            elif rng_scan == 2:

                self.curr_delay = 0.008     # s
                self.curr_step = 1 * self.curr_step
                repeat = self.scanningCur(0.1, ch)
                rng_scan = 3
            elif rng_scan == 3:

                self.curr_delay = 0.005     # s
                self.curr_step = 1 * self.curr_step
                repeat = self.scanningCur(0.2, ch)
                rng_scan = 4
            elif rng_scan == 4:

                self.diff_cur_drift = 1;       # after this case don't care about direction
                self.curr_delay = 0.005     # s
                self.curr_step = 1 * self.curr_step
                repeat = self.scanningCur(0.4, ch)
                rng_scan = 5
            elif rng_scan == 5:

                self.curr_delay = 0.005     # s
                self.curr_step = 1 * self.curr_step
                repeat = self.scanningCur(2.0, ch)
                rng_scan = 1
                no_scan += 1

            if repeat == 2:

                rng_scan = 1
                repeat = 1
                no_scan = 0
                time.sleep(1)

        self.IParam[str(ch)][3] = self.IParam[str(ch)][4]               # previous drift value on lock
        self.IParam[str(ch)][4] = self.IParam[str(ch)][2]               # new drift value on lock
        if self.IParam[str(ch)][5] < 10:                                # to avoide raising to much of drift_no
            self.IParam[str(ch)][5] += 1

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

            if self.freq_diff < std_freq and self.trans > self.tranLevel:
                
                self.PztParam[str(ch)][2] = curr_val
                return 2        # to start scaning in small range
            
            # # if it is not on cavity lock check these
            # if self.chName[str(ch)][8] == 0:
                    
            #     if self.freq_diff < std_freq * 2 and per == 0.2:    # very good condition
                    
            #         self.PztParam[str(ch)][2] = curr_val
            #         return 2
            #     elif self.freq_diff < std_freq * 4 and per == 0.4:    # good condition
                    
            #         return 3
            #     elif self.freq_diff < std_freq * 6 and per == 2.0:    # bad condition
                    
            #         return 4
            
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
            if not self.relocking:
                break
            self.getInfo(ch)
            i += 1

        return 1
    
    def piezo_scan(self, ch):

        repeat = 1
        rng_scan = 1
        no_scan = 0
        max_no_scan = 5
        t1 = time.time()    # to keep for saving data

        while self.relocking and repeat > 0:

            if self.freq_diff < (self.refDataInfo[str(ch)][1] - self.refDataInfo[str(ch)][2]) \
                and self.trans > self.tranLevel:
                break

            # if is not able to find the Mode, stop searching
            if no_scan == max_no_scan:
                repeat = 0
                self.chName[str(ch)][2] = 0
                print("[NOT FOUND] Target frequency is not in the range of scan")
                break

            if rng_scan == 1:

                self.piezo_delay = 0.01     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.05, ch)
                rng_scan = 2
            elif rng_scan == 2:

                self.piezo_delay = 0.008     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.1, ch)
                rng_scan = 3
            elif rng_scan == 3:

                self.piezo_delay = 0.005     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.2, ch)
                rng_scan = 4
            elif rng_scan == 4:

                self.diff_piezo_drift = 1;       # after this case don't care about direction
                self.piezo_delay = 0.005     # s
                self.piezo_step = 1 * self.piezo_step
                repeat = self.scanning(0.4, ch)
                rng_scan = 5
            elif rng_scan == 5:

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

        self.PztParam[str(ch)][9] = 60                                          # set first drift time on 60
        self.PztParam[str(ch)][8] = time.time()                                 # for laser drift
    
    def locking(self, ch):

        self.iCurrVal = self.IParam[ch][2]
        self.pztCurrVal = self.PztParam[ch][2]
        # scan_range = 30

        if self.chName[ch][2] == 1:

            self.lc.setOutput(self.chName[ch][5], self.pztCurrVal)
            self.pztState = True
        else:
            self.pztState = False

        if self.chName[ch][3] == 1:

            self.lc.setOutput(self.chName[ch][6], self.iCurrVal)
            self.currState = True
        else:
            self.currState = False

        time.sleep(0.01)
        self.getInfo(int(ch))

        # check single mode or multimode
        if self.currState and (self.freq_diff > self.freqStep or self.noPeaks_diff > self.noP_diff_thr):

            # drift_no 
            if self.IParam[ch][5] >= 2:
            
                # new - prevoius, laser drift
                self.diff_cur_drift = self.IParam[ch][4] - self.IParam[ch][3]
            else:

                # positive direction
                self.diff_cur_drift = 1

            print('current scan: ' + ch)
            self.current_scan(int(ch))
            # save new refrence data
            if self.chName[ch][3] == 1 and self.freq_diff < self.refDataInfo[str(ch)][1] \
                and self.trans > self.tranLevel and self.noPeaks_diff < self.noP_diff_thr:

                self.refDataInfo[ch][0] = self.noPeaksSpec
            

        # check frequency target
        if self.pztState and (self.freq_diff >= self.refDataInfo[ch][1] or (self.trans < self.tranLevel and self.trans > -1)):
            
            # drift_no 
            if self.PztParam[ch][7] >= 2:

                # new - prevoius, laser drift
                self.diff_piezo_drift = self.PztParam[ch][4] - self.PztParam[ch][3]
                # stop - start, is duration of keeping lock
                self.diff_t_drift = self.PztParam[ch][6] - self.PztParam[ch][5]
            else:

                # positive direction
                self.diff_piezo_drift = 1
                self.diff_t_drift = 1

            t0 = time.time()
            self.piezo_scan(int(ch))
            self.relock_event[ch]['time'].append(t0)
            self.relock_event[ch]['long'].append((time.time() - t0))
        # else:
        #     self.pztState = False

        self.relockingCavity = False
        self.relocking = False
    
    def laserDrift(self):

        for i in self.chName:

            # if piezo and laser drift are true go inside
            if self.chName[i][2] == 1 and self.chName[i][10] == 1:

                # if time is more than of drift time and number of drift is more than 2 start drifting
                if (time.time() - self.PztParam[i][8]) > self.PztParam[i][9] and self.PztParam[i][7] > 2:

                    # new - prevoius, laser drift
                    self.diff_piezo_drift = self.PztParam[i][4] - self.PztParam[i][3]
                    # to avoid large numbers in laser drift
                    if abs(self.diff_piezo_drift) < self.piezo_step:
                        self.diff_piezo_drift = (self.diff_piezo_drift / abs(self.diff_piezo_drift)) * self.piezo_step

                    self.diff_t_drift = self.PztParam[i][6] - self.PztParam[i][5]

                    if self.diff_t_drift > 10:
                        laser_drift = self.diff_t_drift * self.piezo_step / abs(self.diff_piezo_drift)
                    else:
                        laser_drift = 0

                    if self.diff_piezo_drift < 0:
                        curr_val = self.PztParam[i][2] - self.piezo_step
                    else:
                        curr_val = self.PztParam[i][2] + self.piezo_step
                    
                    print('Drift ' + self.chName[i][0])
                    self.lc.setOutput(self.chName[i][5], curr_val)
                    self.PztParam[i][2] = curr_val
                    self.PztParam[i][8] = time.time()
                    # after first drift, start correction every laser_drift * i
                    self.PztParam[i][9] = np.ceil(laser_drift * 1.3)
                    if self.PztParam[i][9] < 5:
                        self.PztParam[i][9] = 5
    
    def analyse(self):

        for i in self.chName:

            if self.chName[i][2] == 1 or self.chName[i][3] == 1:

                self.getInfo(int(i))
                print(self.chName[i][0] + ' ' + str(self.freqCh))

                # if it is not cavity lock check freq
                if self.chName[i][8] == 0 and \
                    (self.freq_diff >= self.refDataInfo[i][1] or self.noPeaks_diff > self.noP_diff_thr):
                    
                    # if it is not on locking process go inside
                    if not self.relocking:
                        
                        self.relocking = True
                        self.no_rel += 1
                        print('start relocking... ', self.no_rel, ' times', ' at ', time.ctime())
                        # start thread for locking
                        locking_thread = threading.Thread(target=self.locking, args=(i))
                        locking_thread.start()
                        break
                    else:
                        break

    def update(self):

        # start thread for monitoing transmission
        for i in self.chName:
            if self.chName[i][8] == 1 and (self.chName[i][2] == 1 or self.chName[i][3] == 1):

                self.monitoring = True
                # start thread for monitoring cavity transmission
                event = threading.Event()
                cavity_thread = threading.Thread(target=self.monitor_cavity, args=(event,)) # add comma after non iterble args to avoid error
                cavity_thread.start()
                break
        
        t0S = time.time()
        t0A = time.time() - 60      # to start analyse instantly
        
        while True:

            if not self.relocking and self.relockingCavity:

                self.relocking = True
                self.no_rel += 1
                print('start relocking... ', self.no_rel, ' times', ' at ', time.ctime())
                # start thread for locking
                locking_thread = threading.Thread(target=self.locking, args=(self.relockingCh))
                locking_thread.start()
            # analyse every x s, if it is not on locking process
            elif not self.relocking and (time.time() - t0A) >= 60:

                self.analyse()
                if not self.relocking:
                    t0A = time.time()
            elif not self.relocking:
                
                self.laserDrift()
                # every 5 s check the wavemeter to keep it awake should be less than of time out (20 s)
                try:
                    
                    # if there is no other communication go inside
                    if not self.communicating:
                        
                        self.communicating = True
                        self.wlm.keepAwake()
                        self.communicating = False
                except Exception as e:
                    
                    # try to reconnect again
                    # try:
                        
                    #     # check if connection is not closed
                    #     try:
                    #         self.wlm.disconnect()
                    #     except Exception:
                    #         pass
                    #     self.wlm = Client.wlmClient(time_out=60)
                    #     self.wlm.connect(ip = self.general['IP'], port = self.general['PORT'])
                    #     self.wlm.setPrec(self.general['WLMPrec'])
                    # except Exception as e:
                    #     print(f"[ERROR] {e}")
                    #     break
                    pass

            # save data and reconnect to wlm every x s
            if not self.relocking and (time.time() - t0S) >= 300:

                try:

                    self.save_data()
                    t0S = time.time()
                    # try:

                    #     self.wlm.disconnect()
                    #     time.sleep(0.5)
                    #     self.wlm = Client.wlmClient(time_out=60)
                    #     self.wlm.connect(ip = self.general['IP'], port = self.general['PORT'])
                    #     self.wlm.setPrec(self.general['WLMPrec'])
                    # except Exception as e:
                    #     pass
                except Exception:
                    pass
            
            # time.sleep(5)
            try:
                time_over = inputimeout(prompt='End (y/n): ', timeout=2)
                if time_over == "y":
                    break
                else:
                    print('\033[A', end="")
            except Exception:
                print('\033[A', end="")

        if self.monitoring:

            event.set()
            self.relocking = False
            self.monitoring = False
            # wait for the thread to finish
            cavity_thread.join()
        elif self.relocking:
            self.relocking = False
        
        # print("Wait to Stop Relocking...")



if __name__ == '__main__':

    app = AutoRelocking()
    app.setReference()

    app.update()

    app.close()


