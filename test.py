
import json

general = {'path': 'C:\\Users\\stront\\Mehrdad\\AutoRelocking_ECDL_Python',
            'dllpath': 'C:\\Windows\\System32\\wlmData.dll',
            'WlmVer': '491'}
chName = {'1': ['1: Blue', '325.2520', 0, 0, 0, '', '', ''], '2': ['2:', '0', 0, 0, 0, '', '', ''], '3': ['3:', '0', 0, 0, 0, '', '', ''],\
                       '4': ['4: TiSa', '368.5554', 0, 0, 0, '', '', ''], '5': ['5: Re-Pumper(679)', '441.3327', 1, 0, 0, '', '', ''],\
                       '6': ['6: Re-Pumper(707)', '423.9135', 1, 0, 0, '', '', ''], '7': ['7: Red Mot', '434.8291', 0, 0, 0, '', '', ''], \
                       '8': ['8: Clock', '429.2284', 0, 0, 0, '', '', '']}
IParam = {'1': [-1.0, 1.0, 0, '+'], '2': [-1.0, 1.0, 0, '+'], '3': [-1.0, 1.0, 0, '+'], '4': [-1.0, 1.0, 0, '+'],\
                       '5': [-1.0, 0.01, 0, '+'], '6': [-1.0, 0.15, 0, '+'], '7': [-1.0, 1.0, 0, '+'], '8': [-1.0, 1.0, 0, '+']}
        # [min, max, last_value, prev_state]
PztParam = {'1': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0], '2': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0], '3': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0], '4': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0],\
                         '5': [-2.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0], '6': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0], '7': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0], '8': [-3.0, 3.0, 0, 0.0, 1.0, 0.0, 0.0, 0.0]}
refDataInfo = {'1': [0, 0.0001, 0.00005, 0], '2': [0, 0.0001, 0.00005, 0], '3': [0, 0.0001, 0.00005, 0],\
                            '4': [0, 0.0001, 0.00005, 0], '5': [0, 0.00004, 0.00001, 0], '6': [0, 0.00004, 0.00001, 0], \
                            '7': [0, 0.0003, 0.00025, 0], '8': [0, 0.0003, 0.00025, 0]}

data = {'general': [general], 
        'chName' : [{'description':'[name, target frequency, PiezoRelockMode (0 or 1), CurrentRelockMode (0 or 1), update (0 or 1), portNamePiezo, portNameCurrent, portNameInput]'}, 
                    chName],
        'IParam' : [{'description':'[min, max, last_value, prev_state (+ or -)]'}, IParam], 
        'PztParam' : [{'description':'[min, max, last_value, piezo_drift0, piezo_drift1, t_drift0, t_drift1, drift_no]'}, PztParam], 
        'refDataInfo' : [{'description':'[no peaks diff, freq_diff_thr, freq_diff_std, has_refData (0 or 1)]'}, refDataInfo]}

json_string = json.dumps(data, indent=4)
# print(json_string)

with open('setting.json', 'w') as outfile:
    outfile.write(json_string)

# with open('setting.json') as json_file:
#     data = json.load(json_file)
#     # print(data['chName'][1])

# chName = (data['general'][0]['path'])
# print((chName))

# print(data['5'][1])