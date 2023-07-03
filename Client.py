######################################################################################################
# @author Mehrdad Zarei <mzarei@umk.pl>
# @date 2021.07.28
# @version 0
#
# @brief client to get wavelength meter information from server
#
######################################################################################################



import time
import json
import socket
import numpy as np



class wlmClient:

    def __init__(self, client = None, time_out = 20):
        
        self.header = 64
        self.format = "utf-8"
        self.discon_msg = "!DISCONNECT"
        self.communicating = False
        self.switch = 1
        self.exp = 1
        self.expup = 3
        self.expdown = 3
        self.wavel = 0
        self.freq = 0
        self.ratio = 1
        self.spec = []
        self.spectrum_list = []
        
        if client is None:

            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(time_out)
        else:
            self.client = client

    def connect(self, ip = "192.168.0.154", port = 5015):
        
        self.client.connect((ip, port))

    def disconnect(self):

        obj_send = {"STATUS": self.discon_msg}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        self.my_send(message)

        self.client.close()

    def my_send(self, msg):

        # wait till other communication is done
        while self.communicating:
            time.sleep(0.01)
        self.communicating = True
        total_sent = 0
        MSGLEN = len(msg)
        send_length = str(MSGLEN).encode(self.format)
        send_length += b' ' * (self.header - len(send_length))
        # print(send_length)

        # waiting for reply
        while True:

            try:
                msg_recv = self.client.recv(1)
            except Exception:
                msg_recv = '0'

            if msg_recv == '':
                self.communicating = False
                return -1
            try:
                if int(msg_recv) == 1:
                    break
                elif int(msg_recv) == 0:
                    self.communicating = False
                    return 0
            except Exception:
                break

        # send msg len
        while total_sent < self.header:

            sent = self.client.send(send_length[total_sent:])
            if sent == 0:
                self.communicating = False
                return -1
            total_sent += sent

        # waiting for reply
        while True:

            try:
                msg_recv = self.client.recv(1)
            except Exception:
                msg_recv = '0'

            if msg_recv == '':
                self.communicating = False
                return -1
            try:
                if int(msg_recv) == 1:
                    break
                elif int(msg_recv) == 0:
                    self.communicating = False
                    return 0
            except Exception:
                break

        # send msg
        total_sent = 0
        while total_sent < MSGLEN:

            sent = self.client.send(msg[total_sent:])
            if sent == 0:
                self.communicating = False
                return -1
            total_sent = total_sent + sent

        # waiting for reply
        while True:

            try:
                msg_recv = self.client.recv(1)
            except Exception:
                msg_recv = '0'

            if msg_recv == '':
                self.communicating = False
                return -1
            try:
                if int(msg_recv) == 1:
                    break
                elif int(msg_recv) == 0:
                    self.communicating = False
                    return 0
            except Exception:
                break

        self.communicating = False

    def my_recv(self):

        # wait till other communication is done
        while self.communicating:
            time.sleep(0.01)
        self.communicating = True
        chunks = []
        bytes_recd = 0

        try:
            self.client.send(bytes("1".encode(self.format)))
        except Exception:
            self.communicating = False
            return '0'

        # recv msg len
        while bytes_recd < self.header:

            chunk = self.client.recv(min(self.header - bytes_recd, self.header))
            if chunk == '':
                self.communicating = False
                return '-1'
            chunks.append(chunk.decode(self.format))
            bytes_recd += len(chunk)

        msg_len = ''.join(chunks)
        # print(msg_len)
        try:
            MSGLEN = int(msg_len)
            self.client.send(bytes("1".encode(self.format)))
        except :
            self.client.send(bytes("0".encode(self.format)))
            self.communicating = False
            return '0'
        # print(MSGLEN)
        chunks = []
        bytes_recd = 0

        # recv msg
        while bytes_recd < MSGLEN:

            chunk = self.client.recv(min(MSGLEN - bytes_recd, 1024))
            if chunk == '':
                self.communicating = False
                return '-1'
            chunks.append(chunk.decode(self.format))
            bytes_recd += len(chunk)

        self.client.send(bytes("1".encode(self.format)))

        self.communicating = False
        return ''.join(chunks)

    def extractData(self, obj_recv = {}):

        if "SWITCH_MODE" in obj_recv:
            self.switch = obj_recv["SWITCH_MODE"]

        if "EXP_AUTO" in obj_recv:
            self.exp = obj_recv["EXP_AUTO"]

        if "EXP_UP" in obj_recv:
            self.expup = obj_recv["EXP_UP"]

        if "EXP_DOWN" in obj_recv:
            self.expdown = obj_recv["EXP_DOWN"]
        
        if "WAVEL" in obj_recv:
            self.wavel = obj_recv["WAVEL"]

        if "FREQ" in obj_recv:
            self.freq = obj_recv["FREQ"]
        
        if "RATIO" in obj_recv:
            self.ratio = obj_recv["RATIO"]
        
        if "SPEC" in obj_recv:
            
            self.spectrum_list = []
            self.spec = obj_recv["SPEC"]

            self.spectrum_list = np.divide(self.spec, float(self.ratio))
            self.spectrum_list = np.interp(np.linspace(0, 1024, 2048), np.arange(1024), self.spectrum_list)
    
    def keepAwake(self):

        obj_send = {"SEND": " "}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
    
    def setSwitchMode(self, mode = 1):

        # mode 0 for single mode and 1 for switch mode
        obj_send = {"WLM_RUN": 1, "SWITCH_MODE": mode}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
    
    def getSwitchMode(self):

        obj_send = {"WLM_RUN": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return self.switch
    
    def setExpoAuto(self, mode = 1):

        # mode 0 for manual expo and 1 for auto axpo
        obj_send = {"WLM_RUN": 1, "EXP_AUTO": mode}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
    
    def getExpoAuto(self):

        obj_send = {"WLM_RUN": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return self.exp
    
    def setExpUp(self, val = 3):

        obj_send = {"WLM_RUN": 1, "EXP_UP": val}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

    def getExpUp(self):

        obj_send = {"WLM_RUN": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return self.expup
    
    def setExpDown(self, val = 3):

        obj_send = {"WLM_RUN": 1, "EXP_DOWN": val}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

    def getExpDown(self):

        obj_send = {"WLM_RUN": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return self.expdown
    
    def setPrec(self, val = 5):

        obj_send = {"WLM_RUN": 1, "PREC": val}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
    
    def getWavelength(self, ch = 1):

        obj_send = {"WLM_RUN": 1, "CH": ch, "WAVEL": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed

        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return self.wavel

    def getFrequency(self, ch = 1):

        obj_send = {"WLM_RUN": 1, "CH": ch, "FREQ": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
            
        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}

        self.extractData(obj_recv)
        
        return self.freq

    def getSpectrum(self, ch = 1):

        obj_send = {"WLM_RUN": 1, "CH": ch, "SPEC": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
            
        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return self.spectrum_list

    def getAll(self, ch = 1):

        obj_send = {"WLM_RUN": 1, "CH": ch, "WAVEL": 1, "FREQ": 1, "SPEC": 1}
        data = json.dumps(obj_send)
        message = data.encode(self.format)
        err = self.my_send(message)

        if err == 0:
            return -31          # retry again
        elif err == -1:
            self.client.close()
            return -30          # connection is closed

        msg = self.my_recv()
        if msg == '0':
            return -31          # retry again
        elif msg == '-1':
            self.client.close()
            return -30          # connection is closed
            
        try:
            obj_recv = json.loads(msg)
        except :
            obj_recv = {}
        
        self.extractData(obj_recv)

        return {"wavelength": self.wavel, "freq": self.freq, "spec": self.spectrum_list}



