import re
import serial.tools.list_ports
import threading

data = []

class UartDataThread(threading.Thread):
    def __init__(self, databuffer, name="DataThread", sleepperiod=0.0, port="", baudrate=115200):
        # sleeper event and period
        self._stopevent = threading.Event()
        self._sleepperiod = sleepperiod

        # result queue and handler thread
        self._databuffer = databuffer

        # portlist and logic variables
        self._isconnected = False
        self._portlist = []

        # serial instance variables
        self._serialInst = serial.Serial()
        self._serialInst.timeout = 0
        self._serialInst.baudrate = baudrate
        self._serialInst.port = port

        threading.Thread.__init__(self, name=name)


    def run(self):
        """ main code execution """
        self.connect() # connect to com port
        
        if self._isconnected:
            while not self._stopevent.isSet():
                self.getData()
                self._stopevent.wait(self._sleepperiod)

    def stop(self, timeout=None):
        self._stopevent.set()
        self.disconnect()
        self._serialInst.close()
        threading.Thread.join(self, timeout)
        
    def connect(self):
        """ connect to COM port """
        try:
            self._serialInst.open()
            self._isconnected = True
            print("connected to: '" + self._serialInst.port + "'")
        except:
            print("error connecting to: '" + self._serialInst.port + "'")
            self._isconnected = False
            self._stopevent.set()


    def disconnect(self):
        try:
            self._serialInst.close()
            print("disconnected from: '" + self._serialInst.port + "'")
        except:
            print("error closing connection with: '" + self._serialInst.port + "'")
            self._stopevent.set()

    def getData(self):
        if self._serialInst.in_waiting:
            try:
                packet = self._serialInst.readline()
                packet_data = packet.decode(errors='ignore')
            except:
                print("error during receiving package")

            try:
                n = re.findall('[0-9]{4,5}.[0-9]+', packet_data)

                # do something with data
                for match in n:
                    try:
                        self._databuffer.append(float(match))
                    except:
                        print("error")
                    print(match)
                    return match
            except:
                print("error")
                # do nothing