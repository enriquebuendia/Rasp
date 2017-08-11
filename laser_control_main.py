#!/usr/bin/python -d
# -*- coding: utf-8 -*-

import sys 
import logging
from PyQt4 import QtCore, QtGui
from telescope_server import Telescope_Server
import coords

class LaserControlMain(QtGui.QMainWindow):
    #Señal para actualizar el FOV de Stellarium
    act_stell_pos = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super(LaserControlMain, self).__init__(parent)
        (self._ra, self._dec) = ("0h0m0s", "0º0'0''")

        self.Server = Telescope_Server(pos_signal=self.act_stell_pos)
        self.Server.daemon = True
        self.Server.start()
        self.initUI()
        
        self.Server.stell_pos_recv.connect(self.stellariumRecv)

    def initUI(self):
        self.lcd_az = QtGui.QLCDNumber(self)
        #lcd_el = QtGui.QLCDNumber(self)
        #self.lcd_az.setDigitCount()

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.lcd_az)
        #vbox.addWidget(lcd_el)

        self.setLayout(vbox)
        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Posicion Astro')
        self.show()

    def stellariumRecv(self, ra, dec, mtime):
        ra = float(ra)
        dec = float(dec)
        mtime = float(mtime)
        logging.debug("%s" % coords.toJ2000(ra, dec, mtime))
        (sra, sdec, stime) = coords.eCoords2str(ra, dec, mtime)
        (self._ra, self._dec) = (sra, sdec)
        print str(sra) + ',' + str(sdec)
        self.lcd_az.display(sra)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    app_gui = LaserControlMain()
    app_gui.show()
    sys.exit(app.exec_())

