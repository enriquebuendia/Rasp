#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import serial
import re
import time
from serial.tools import list_ports
from threading import Thread, Event
from PyQt4 import QtCore

class comSerial(QtCore.QThread):

    readAntena = QtCore.pyqtSignal(str,str,str,str,str,str,str)

    def __init__(self, portSerial, baudRate = 57600, timeout = 1):
        QtCore.QThread.__init__(self, None)
        self.finished = Event()

        self.seriePort = serial.Serial(portSerial, baudRate ,timeout = timeout)

        self.seriePort.setDTR(False)
        time.sleep(1)
        self.seriePort.flushInput()
        self.seriePort.setDTR(True)

    def run(self):
        while not self.finished.is_set():
            if not self.finished.is_set():
                wordSerie = self.readSer()
                self.getWord(wordSerie,9)

    def readSer(self):
        check = 0
        word = ''
        readSerial = self.seriePort.read(1)
        if readSerial == '#':
            readSerial = self.seriePort.read(1)
            while readSerial != '*':
                check = check + 1
                if check >= 150:
                    print "Error 1. No se encuentra el final de la cadena!!!"
                    word = 'ERROR1'
                    break
                word = word + readSerial
                readSerial = self.seriePort.read(1)
            print word
            readSerial = ''
            self.seriePort.flushInput()
        return word

    def getWord(self,wordWork,param):
        coma = 0
        vectStatus = ['']*param

        if wordWork != '':
            if wordWork != 'ERROR1':
                for i in range(len(wordWork)):
                    if wordWork[i] == ',':
                        coma = coma + 1;
                    else:
                        if coma == 9:
                            break
                        vectStatus[coma] = vectStatus[coma] + wordWork[i]               
                if vectStatus[7] == 'O' and vectStatus[8] == 'K':
                    self.readAntena.emit(vectStatus[0],vectStatus[1],vectStatus[2],vectStatus[3],vectStatus[4],vectStatus[5],vectStatus[6])
                else:
                    print "Error 2. Envio corrupto!!!"
            
    def writeWord(self,az,el,mode,vel,m_az,m_el,h,ori):
        word = '#' + '{0:.3f}'.format(az) + ',' + '{0:.3f}'.format(el) + ',' + str(mode) + ',' + str(vel) + ',' + str(m_az) + ',' + str(m_el) + ',' + str(h) +  "*\n"#',' + str(ori) + '*' 
        #print word
        self.seriePort.write(word)

    def cancel(self):
        self.finished.set()

def availablePorts():
    available = []
    
    #Se buscan los puertos Serie:
    checkSER = re.compile('/dev/tty(USB|ACM)[0-9]+')

    for port in list_ports.comports():
        if checkSER.match(port[0]):
            available.append(port[0])
    
    return available

import time
s=availablePorts()
a = comSerial('COM10')
while True:
    a.readSer()
