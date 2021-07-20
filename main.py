import sys, datetime, os
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtCore import pyqtSignal, pyqtSlot
import pyqtgraph as pg
from pyqtgraph.widgets.PlotWidget import PlotWidget

import queue

import serial.tools.list_ports
import re

#from serialThread import UartDataThread
import time

serialInst = serial.Serial()
portlist = []

timeBuffer = []
dataBuffer = []


class GraphicUpdateThread(QtCore.QThread):

    update_graph_event = pyqtSignal()

    def __init__(self):
        QtCore.QThread.__init__(self)
        self._stopevent = False

    def __del__(self):
        self.wait()

    @pyqtSlot(bool)
    def setStopevent(self, bool):
        self._stopevent = bool

    def run(self):
        """ main code execution """
        while not self._stopevent:
            self.update_graph_event.emit()
            time.sleep(1)

    def stop(self, timeout=None):
        self._stopevent = True
        self.quit()



class UartDataThread(QtCore.QThread):

    add_measure_event = pyqtSignal(float)

    def __init__(self, sleepperiod=0.0):
        # sleeper event and period
        self._stopevent = False
        self._sleepperiod = sleepperiod

        # portlist and logic variables
        self._isconnected = False
        self._portlist = []

        QtCore.QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        """ main code execution """        
        if self._isconnected:
            while not self._stopevent:
                self.get_data()
                time.sleep(self._sleepperiod)

    def stop(self, timeout=None):
        self._stopevent = True
        self.disconnect()
        self._serialInst.close()
        self.quit()

    @pyqtSlot(str)
    def connect(self, port="", baudrate=115200):
        """ connect to COM port """
        # serial instance variables
        self._serialInst = serial.Serial()
        self._serialInst.timeout = 0
        self._serialInst.baudrate = baudrate
        self._serialInst.port = port
        
        try:
            self._serialInst.open()
            self._isconnected = True
            print("connected to: '" + self._serialInst.port + "'")
        except:
            print("error connecting to: '" + self._serialInst.port + "'")
            self._isconnected = False
            self._stopevent = True

    def disconnect(self):
        try:
            self._serialInst.close()
            self._isconnected = False
            print("disconnected from: '" + self._serialInst.port + "'")
        except:
            print("error closing connection with: '" + self._serialInst.port + "'")
            self._stopevent.set()

    def get_data(self):
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
                        if float(match) is not None:
                            #self.add_measure(float(match))
                            self.add_measure_event.emit(float(match))
                            print(match)
                    except:
                        print("error")

                    return match
            except:
                print("error")
                # do nothing

class Ui(QtWidgets.QMainWindow):

    start_update_thread_signal = pyqtSignal()
    stop_update_thread_signal = pyqtSignal()
    update_thread_set_stopevent_signal = pyqtSignal(bool)
    
    start_data_thread_signal = pyqtSignal()
    stop_data_thread_signal = pyqtSignal()
    connect_data_thread_signal = pyqtSignal(str)
    disconnect_serial_thread_signal = pyqtSignal()
    

    def __init__(self):
        super(Ui, self).__init__() # call inherited class __init__ methods
        self.setupUi()
        self.com_isconnected = False

        self._GraphicUpdateThread = GraphicUpdateThread()
        self._GraphicUpdateThread.update_graph_event.connect(self.plotData)
        self.start_update_thread_signal.connect(self._GraphicUpdateThread.start)
        self.stop_update_thread_signal.connect(self._GraphicUpdateThread.stop)
        self.update_thread_set_stopevent_signal.connect(self._GraphicUpdateThread.setStopevent)

        self._UartDataThread = UartDataThread(sleepperiod=0.1)
        self._UartDataThread.add_measure_event.connect(self.add_measure)
        self.start_data_thread_signal.connect(self._UartDataThread.start)
        self.stop_data_thread_signal.connect(self._UartDataThread.stop)
        self.connect_data_thread_signal.connect(self._UartDataThread.connect)
        self.disconnect_serial_thread_signal.connect(self._UartDataThread.disconnect)

        

          
    def setupUi(self):
        uic.loadUi('bsensgui.ui', self)
        self.comselection_init()
        self.measuretable_init()
        
        # debug
        #self.testbutton = self.findChild(QtWidgets.QPushButton, "testButton")
        #self.testbutton.clicked.connect(self.add_measure)

    @pyqtSlot()
    def plotData(self):
        self.graphicPlotWidget.plot(timeBuffer, dataBuffer)

    @pyqtSlot(float)
    def add_measure(self, freq):
        curr_row_ = self.MeasureTable.rowCount()    # get current number of entries
        self.MeasureTable.setRowCount(curr_row_+1)  # +1 for new entry
        curr_time_ = datetime.datetime.now()   # get current time

        # write data to table
        self.MeasureTable.setItem(curr_row_, 0, QtWidgets.QTableWidgetItem(str(curr_time_)))
        self.MeasureTable.setItem(curr_row_, 1, QtWidgets.QTableWidgetItem(str(freq)))

        # resize and scroll
        self.MeasureTable.resizeRowsToContents()
        self.MeasureTable.scrollToBottom()

        timeBuffer.append(curr_time_.timestamp())
        dataBuffer.append(freq)

    def comselection_init(self):
        # init com buttons
        self.com_connectbutton = self.findChild(QtWidgets.QPushButton, "General_com_connectbutton")
        self.com_connectbutton.clicked.connect(self.com_connect)
        self.com_refreshbutton = self.findChild(QtWidgets.QPushButton, "General_com_refreshbutton")
        self.com_refreshbutton.clicked.connect(self.com_refresh)

        # init combobox
        self.comcombobox = self.findChild(QtWidgets.QComboBox, "General_com_portselection")
        self.com_refresh()

        # init statuslabel
        self.general_statuslabel = self.findChild(QtWidgets.QLabel, "General_statuslabel")
        self.general_statuslabel.setText("")
        
        # disable combobox if contents are empty
        if not self.comcombobox.currentText() or not self.comcombobox.count() > 0:
            self.comcombobox.setEnabled(False)
            self.com_connectbutton.setEnabled(False)
        
    def com_refresh(self):
        # get available ports
        ports = serial.tools.list_ports.comports()
        portlist = []
        for port in ports:
            portlist.append(str(port))
            #print(str(port))

        # clear combobox content
        while self.comcombobox.count()>0:
            self.comcombobox.removeItem(0)

        # add all found ports to combobox
        self.comcombobox.addItems(portlist)
        #print(portlist)

        # if combobox not empty, enable it
        if self.comcombobox.count() > 0:
            self.comcombobox.setEnabled(True)
            self.com_connectbutton.setEnabled(True)

    def com_connect(self):
        if self.com_isconnected:
            
            # close thread
            self.disconnect_serial_thread_signal.emit()
            #self.stop_data_thread_signal.emit()
            #self.stop_update_thread_signal.emit()
            self.update_thread_set_stopevent_signal.emit(bool(True)) # halt update loop

            print("THREAD STOPPED")

            self.com_connectbutton.setText("connect")
            self.comcombobox.setEnabled(True)
            self.com_refreshbutton.setEnabled(True)
            self.com_isconnected = False
            self.general_statuslabel.setText("")

        else:
            # if current combobox value is not empty
            if self.comcombobox.currentText():
                # use regex to search for COMx string
                p = re.compile('com[0-9]*', re.IGNORECASE)
                m = p.match(self.comcombobox.currentText())
                print(m.group())

                # start thread
                try:
                     # connect to serial
                    self.connect_data_thread_signal.emit(m.group())
                    self.start_data_thread_signal.emit()

                    try:
                        self.start_update_thread_signal.emit()
                    except:
                        self.update_thread_set_stopevent_signal.emit(bool(False)) # enable update loop
                    print("THREAD STARTED")

                    self.com_isconnected = True
                    self.com_connectbutton.setText("disconnect")
                    self.com_refreshbutton.setEnabled(False)
                    self.comcombobox.setEnabled(False)
                    self.general_statuslabel.setText("Connected to: " + m.group())

                except:
                    print("error starting thread")

            else:
                print("error: port not found!")

    def measuretable_init(self):
        self.MeasureTable = self.findChild(QtWidgets.QTableWidget, "Measure_TableWidget")
        self.MeasureTable.setHorizontalHeaderLabels(["Time", "Frequency"]) # set table headers


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Ui() # load .ui file 
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)