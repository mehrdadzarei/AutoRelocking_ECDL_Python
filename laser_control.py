######################################################################################################
# @author Mehrdad Zarei <mzarei@umk.pl>
# @date 2021.08.10
# @version 0
#
# @brief control lasre's parameters with NI_USB_6229
#
######################################################################################################



from inspect import Attribute
import nidaqmx
from nidaqmx.constants import TerminalConfiguration



class LaserControl:

    # def __init__(self):
        
        # self.chPzt = {'1': '', '2': '', '3': '', '4': '',\
        #             '5': 'Dev2/ao2', '6': 'Dev2/ao0', '7': '', '8': ''}
        # self.chI = {'1': '', '2': '', '3': '', '4': '',\
        #               '5': 'Dev2/ao3', '6': 'Dev2/ao1', '7': '', '8': ''}

        # self.set_I('6', 0)
        # self.set_Pzt('6', 0)
        # self.RSE = 10083

    def setOutput(self, port, val):

        with nidaqmx.Task() as task:

            try:
                task.ao_channels.add_ao_voltage_chan(port)
            except nidaqmx.DaqError:
                return False
            
            try: 
                task.write([round(val, 3)], auto_start=True, timeout=0.0)
            except :
                pass

    def getInput(self, port):

        with nidaqmx.Task() as task:

            try:
                task.ai_channels.add_ai_voltage_chan(port, terminal_config=TerminalConfiguration.RSE)
            except nidaqmx.DaqError:
                return -11
            
            try: 
                return task.read()
            except :
                return -12

# a = LaserControl()
# print(a.getInput('Dev1/ai1'))
# a.set_I('Dev2/ao2', 0.0)
# a.set_Pzt('Dev2/ao0', 0.0)
