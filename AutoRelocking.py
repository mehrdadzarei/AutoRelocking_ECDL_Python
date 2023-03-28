######################################################################################################
# @author Mehrdad Zarei <mzarei@umk.pl>
# @date 2023.03.28
# @version 0
#
# @brief re-locking lasers
#
######################################################################################################



import sys, time
import threading
import socket
import numpy as np
from scipy.signal import find_peaks
import wavelength_meter
from wlmConst import *
import laser_control



# path = 'D:\\programming\\KL FAMO\\HighFinesse\\'
path = 'C:\\Users\\UMK\\Documents\\cavity_progs\\py-ws7\\Mehrdad\\'



class AutoRelocking:

    def __init__(self):

        self.wlm = wavelength_meter.WavelengthMeter(dllpath = str(sys.argv[1]), WlmVer = int(sys.argv[2]))
        self.lc = laser_control.LaserControl()
        
        # [name, target frequency, PiezoRelockMode, CurrentRelockMode, update, portNamePiezo, portNameCurrent, portNameInput]
        self.chName = {'1': ['1: Blue', '325.2520', 0, 0, 0, '', '', ''], '2': ['2:', '0', 0, 0, 0, '', '', ''], '3': ['3:', '0', 0, 0, 0, '', '', ''],\
                       '4': ['4: TiSa', '368.5554', 0, 0, 0, '', '', ''], '5': ['5: Re-Pumper(679)', '441.3327', 0, 0, 0, '', '', ''],\
                       '6': ['6: Re-Pumper(707)', '423.9135', 0, 0, 0, '', '', ''], '7': ['7: Red Mot', '434.8291', 0, 0, 0, '', '', ''], \
                       '8': ['8: Clock', '429.2284', 0, 0, 0, '', '', '']}
        # [no peaks diff, freq_diff_thr, freq_diff_std, has_refData]
        self.refDataInfo = {'1': [0, 0.0001, 0.00005, 0], '2': [0, 0.0001, 0.00005, 0], '3': [0, 0.0001, 0.00005, 0],\
                            '4': [0, 0.0001, 0.00005, 0], '5': [0, 0.00004, 0.00001, 0], '6': [0, 0.00004, 0.00001, 0], \
                            '7': [0, 0.0003, 0.00025, 0], '8': [0, 0.0003, 0.00025, 0]}
        self.fname = {'1': path + 'refCh1.txt', '2': path + 'refCh2.txt', '3': path + 'refCh3.txt', '4': path + 'refCh4.txt',\
                       '5': path + 'refCh5.txt', '6': path + 'refCh6.txt', '7': path + 'refCh7.txt', '8': path + 'refCh8.txt'}
        # [min, max, last_value, prev_state]
        self.IParam = {'1': [-1.0, 1.0, 0, '+'], '2': [-1.0, 1.0, 0, '+'], '3': [-1.0, 1.0, 0, '+'], '4': [-1.0, 1.0, 0, '+'],\
                       '5': [-1.0, 0.01, 0, '+'], '6': [-1.0, 0.15, 0, '+'], '7': [-1.0, 1.0, 0, '+'], '8': [-1.0, 1.0, 0, '+']}
        # [min, max, last_value, prev_state]
        self.PztParam = {'1': [-3.0, 3.0, 0, '+'], '2': [-3.0, 3.0, 0, '+'], '3': [-3.0, 3.0, 0, '+'], '4': [-3.0, 3.0, 0, '+'],\
                         '5': [-2.0, 3.0, 0, '+'], '6': [-3.0, 3.0, 0, '+'], '7': [-3.0, 3.0, 0, '+'], '8': [-3.0, 3.0, 0, '+']}

        
        self.height_thr = 150
        self.distance_thr = 20
        self.noP_diff_thr = 8
        self.noP_diff_std = 7
        # self.freq_diff_thr = 0.0001
        # self.freq_diff_std = 0.00005

        try:
                
            with open(path + 'setting.txt', 'r') as f:

                a = f.readlines()
                for i in self.IParam:
                        
                    self.IParam[i][2] = float(a[a.index('channelI ' + i + ':\n') + 1])      # last value
                    self.IParam[i][3] = a[a.index('channelI ' + i + ':\n') + 2][:-1]        # prev state
                for i in self.PztParam:
                        
                    self.PztParam[i][2] = float(a[a.index('channelPzt ' + i + ':\n') + 1])  # last value
                    self.PztParam[i][3] = a[a.index('channelPzt ' + i + ':\n') + 2][:-1]    # prev state
                for i in self.chName:
                        
                    self.chName[i][2] = int(a[a.index('properties ' + i + ':\n') + 1])      # pzt relock mode
                    self.chName[i][3] = int(a[a.index('properties ' + i + ':\n') + 2])      # curr relock mode
                    self.chName[i][4] = int(a[a.index('properties ' + i + ':\n') + 3])      # update
                    self.chName[i][5] = a[a.index('properties ' + i + ':\n') + 4][:-1]      # piezo port name
                    self.chName[i][6] = a[a.index('properties ' + i + ':\n') + 5][:-1]      # current port name
                    self.chName[i][7] = a[a.index('properties ' + i + ':\n') + 6][:-1]      # input port name

                f.close()
        except IOError:
            pass

        for i in self.refDataInfo:
            
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

        self.wlm.run(action = 'show')    # show or hide
        self.wlm.measurement(cCtrlStartMeasurement)   # state : cCtrlStopAll, cCtrlStartMeasurement

    def __del__(self):

        try:
                
            with open(path + 'setting.txt', 'w') as f:

                f.write('\nlast piezo and current relock mode, update, piezo and current port name for each channel:\n')
                for i in self.chName:
                    
                    f.write('properties ' + i + ':\n' + str(self.chName[i][2]) + '\n' + str(self.chName[i][3]) + '\n' +\
                                    str(self.chName[i][4]) + '\n' + str(self.chName[i][5]) + '\n' +\
                                    str(self.chName[i][6]) + '\n' + str(self.chName[i][7]) + '\n')
                    
                f.write('last value and previous state of Current for laser driver:\n')
                for i in self.IParam:
                    
                    f.write('channelI ' + i + ':\n' + str(self.IParam[i][2]) + '\n' + self.IParam[i][3] + '\n')
                
                f.write('\nlast value and previous state of Piezo for laser driver:\n')
                for i in self.PztParam:
                    
                    f.write('channelPzt ' + i + ':\n' + str(self.PztParam[i][2]) + '\n' + self.PztParam[i][3] + '\n')
                
                f.close()
        except IOError:
            pass

    def getSpecificInfo(self, ch):

        self.freqCh = self.wlm.getFrequency(ch)
        if self.freqCh == -4:
            
            self.wlm.setExposureMode(ch, True)
            time.sleep(0.1)
            self.wlm.setExposureMode(ch, False)
            self.freqCh = self.wlm.getFrequency(ch)

        self.diffCh = abs(float(self.chName[str(ch)][1]) - self.freqCh)
        if self.diffCh < 50:
            
            if self.refDataInfo[str(self.ch)][3] == 1:

                spec = self.wlm.spectrum(ch)
                peaksIndSpec, peaksHSpec = find_peaks(spec, height = self.height_thr, distance = self.distance_thr)
                self.noPeaksSpec = len(peaksIndSpec)
                self.noPeaks_diff_ch = abs(self.noPeaksSpec - self.refDataInfo[str(ch)][0])
            else:
                self.noPeaks_diff_ch = -1
        else:
            self.diffCh = -1
            self.noPeaks_diff_ch = -2
    
    def analyse(self):

        for i in self.chName:

            if self.chName[i][2] == 1 or self.chName[i][3] == 1:

                self.getSpecificInfo(int(i))
                print(self.chName[i][0] + ' ' + self.freqCh)

    def update(self):

        while True:

            self.analyse()

            time.sleep(1)


if __name__ == '__main__':

    app = AutoRelocking()

    app.update()


