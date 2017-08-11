#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import numpy as np
import sys
import math
from PyQt4 import QtCore, QtGui
import design
from qled import QLed
from serial.tools import list_ports
from joystick_control import joyStickControl
from comSerie import comSerial, availablePorts
from telescope_server import Telescope_Server
from EcuatorialToHorizontal import EcuToHor
import coords
from tracking import TrackMode
#Grafica Receptor
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import(
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

class GUIControl(QtGui.QMainWindow, design.Ui_controlMontura):

    #Señal para actualizar el FOV de Stellarium
    act_stell_pos = QtCore.pyqtSignal(str, str)
    
    def __init__(self, parent = None):
        super(GUIControl, self).__init__(parent)
        self.setupUi(self)
        self.RT = None
        self.fig_dict = {}
        
        self.m = 0
        self.az = 0
        self.el = 0
        self.m_az = 0
        self.m_el = 0
        self.vel = 0
        self.h = 0
        
        self.newRA = 0
        self.newDEC = 0
        self.sra = 0
        self.sdec = 0

        self.lon = 0
        self.lat = 0

        self.find = False
        self.track = False
        self.sweep = False

        self.i = 0
        self.j = 0
        self.g = 0
        self.k = False

        self.manualGPS = False
        self.timeBarrido = 0.0

        self.ori = 0
        self.yaori = 0

        #Variables de cuadro
        self.pasox = 0
        self.pasoy = 0
        self.tamanox = 0
        self.tamanoy = 0
        self.timeBarrido = 0
        self.totalx = 0
        self.totaly = 0

        self.adc = 0
        self.paro = 0

        self.vectGrap = [0]*50
        
        #Se inician caracteristicas de la tabla
        self.mode.setCurrentIndex(0)

        #Se bloquean algunos campos
        self.textEdit_2.setDisabled(True)
        self.textEdit_3.setDisabled(True)
        self.textEdit.setDisabled(True)
        self.textEdit_4.setDisabled(True)

        #Conexion serie
        self.connectSerial()

        #Se declaran las conexiones de la GUI
        self.mode.currentChanged.connect(self.modeEdit)
        self.toolButton.clicked.connect(self.home)
        self.toolButton_2.clicked.connect(self.editPos)
        self.toolButton_3.clicked.connect(self.unlock)
        
        self.menubar.setNativeMenuBar(False)
        
        #Iniciamos la configuracion inicial
        self.modeEdit()
    
        #Conexiones del Modo Automatico
        self.checkBox.clicked.connect(self.justFirst)
        self.checkBox_2.clicked.connect(self.justSecond)
        self.checkBox_3.clicked.connect(self.justThird)
        self.frame.setDisabled(True)
        self.mode.setTabEnabled(1, False)

        #Conexion con Stellarium
        self.textEdit_11.setDisabled(True)
        self.textEdit_12.setDisabled(True) 

        self.Server = Telescope_Server(pos_signal=self.act_stell_pos)
        self.Server.daemon = True
        self.Server.start()

        self.Server.stell_pos_recv.connect(self.stellariumRead)

        #Menu Bar
        
        #Archivo
        #Abrir Stellaium
        self.actionAbrir_Stellarium.triggered.connect(self.openSte)
        #Salir
        self.actionSalr.triggered.connect(self.closeApp)

        #Posicionamiento
        #Manual
        self.actionManual.triggered.connect(self.getManualGPS)

        #Acerca
        self.actionAcerca.triggered.connect(self.mensaje)

        #Boton Iniciar
        self.pushButton.clicked.connect(self.start)

        #Boton Stop
        self.pushButton_3.clicked.connect(self.stop)
        self.stopAuto = True

        self.mg = 0

        #Graficamos los valores
        self.fig1 = Figure()
        self.f1 = self.fig1.add_subplot(111)
        self.f1.set_ylabel('Potencia')

        self.addmpl(self.fig1)

        #Boton compas
        self.toolButton_4.clicked.connect(self.orientar)

    def orientar(self):
        self.mode.setDisabled(True)
        self.actionAcerca.setDisabled(True)
        self.actionManual.setDisabled(True)
        self.actionAbrir_Stellarium.setDisabled(True)
        self.statusbar.showMessage("Orientando la antena")

        self.ori = 1
        self.acumWord()

    def addmpl(self,fig):
        self.canvas = FigureCanvas(fig)
        self.plotADC.addWidget(self.canvas)
        self.canvas.draw()
        self.toolbar = NavigationToolbar(self.canvas, 
                self, coordinates=True)
        self.plotADC.addWidget(self.toolbar)
    
    def start(self):
        self.pushButton.setDisabled(True)
        os.system('./test')
        self.mg = 0
        if self.track == True or self.sweep == True:
            if self.sweep == True:
                self.timeBarrido = float(self.tiempoBarrido.toPlainText())
                self.pasox = float(self.azPaso.toPlainText())
                self.pasoy = float(self.elPaso.toPlainText())
                self.tamanox = float(self.azVentana.toPlainText())
                self.tamanoy = float(self.elVentana.toPlainText()) 
                self.totalx = math.ceil(self.tamanox/self.pasox)
                self.totaly = math.ceil(self.tamanoy/self.pasoy)
            #Conexion modo track
            self.Track = TrackMode(self.timeBarrido)
            self.Track.lat_lon.connect(self.writeInfo)
            self.Track.start()

    def stop(self):
        self.pushButton.setDisabled(False)
        self.stopAuto = True
        self.Track.cancel()

    def updateData(self, az, el, lat, lon, adc, paro, yaori):
        try:
            self.az = float(az)
            self.el = float(el)
            self.adc = int(adc)
            self.yaori = int(yaori)
            self.paro = int(paro)
        except:
            print self.az
            print self.el
            print self.adc
            print self.yaori
            print self.paro

        #aux = self.vectGrap[1:50]
        #aux.insert(0,self.adc)
        #self.vectGrap = aux

        #self.newGrap

        if self.manualGPS == False:
            if float(lon) > 18000 and float(lat) > 9000:
                self.textEdit_2.setText("Not Found")
                self.textEdit_3.setText("Not Found")
            else:
                self.lon = float(lon)
                self.lat = float(lat)

                lon_ax = 100*float(self.lon)
                lat_ax = 100*float(self.lat)
                
                self.lon = int(abs(lon_ax/10000)) + float((int(abs(lon_ax/100))%100))/60 + (float(int(abs(lon_ax))%100) + abs(lon_ax) - abs(int(lon_ax)))/3600
                self.lat = int(abs(lat_ax/10000)) + float((int(abs(lat_ax/100))%100))/60 + (float(int(abs(lat_ax))%100) + abs(lat_ax) - abs(int(lat_ax)))/3600

                self.textEdit_2.setText('{0:5f}'.format(self.lat))
                self.textEdit_3.setText('{0:5f}'.format(self.lon))

                if lon_ax < 0:
                    self.lon = -1*self.lon
                    self.label_4.setText('W')
                else:
                    self.label_4.setText('E')
                if lat_ax < 0:
                    self.lat = -1*self.lat
                    self.label_3.setText('S')
                else:
                    self.label_3.setText('N')
                
                self.mode.setTabEnabled(1,True)
                self.manualGPS = True

        if self.paro == 1:
            QtGui.QMessageBox.warning(self, 'Warning', "Motores inhabilitados")
            try:
                self.stop()
                self.frame.setDisabled(True)
                self.modoAuto.setDisabled(True)
                self.actionManual.setDisabled(True)
            except:
                print "Fallo al finalizar los motores"
        elif self.paro == 0:
            self.frame.setDisabled(False)
            self.modoAuto.setDisabled(False)
            self.actionManual.setDisabled(False)
            self.vel = 0

        if self.yaori == 1:
            self.writeLCD(0)
            self.mode.setDisabled(False)
            self.actionAcerca.setDisabled(False)
            self.actionManual.setDisabled(False)
            self.actionAbrir_Stellarium.setDisabled(False)
            self.statusbar.showMessage("Orientacion finalizada")
            
        elif self.yaori == 2:
            self.writeLCD(0)
            self.mode.setDisabled(False)
            self.actionAcerca.setDisabled(False)
            self.actionManual.setDisabled(False)
            self.actionAbrir_Stellarium.setDisabled(False)
            self.statusbar.showMessage("NO se pudo orientar satisfactoriamente la antena")
        
        self.textEdit.setText(az)
        self.textEdit_4.setText(el)

    def mensaje(self):
        QtGui.QMessageBox.information(self, 'Acerca', "Control RT V1.0")

    def newGrap(self):
        self.rmmpl()
        self.f1.plot(self.vectGrap)
        self.addmpl(self.fig1)

    def rmmpl(self):
        self.plotADC.removeWidget(self.canvas)
        self.canvas.close()
        self.plotADC.removeWidget(self.toolbar)
        self.toolbar.close()

    def getManualGPS(self):
        self.manualGPS = True
        self.textEdit_2.setDisabled(False)
        self.textEdit_3.setDisabled(False)
        self.mode.setTabEnabled(1,True)

    def openSte(self):
        os.system('stellarium &')

    def closeApp(self):
        self.Server.close_socket()
        self.close()
            
    def stellariumRead(self, ra, dec, mtime):
        ra = float(ra)
        dec = float(dec)
        mtime = float(mtime)
        (self.sra, self.sdec, stime) = coords.eCoords2str(ra, dec, mtime)

        if self.find == True or self.mg < 1:
            self.writeInfo()        

    def writeInfo(self):
        self.mg = 1
        
        self.newRA = 180*coords.hourStr_2_rad(self.sra)/(math.pi*15)
        self.newDEC = 180*coords.degStr_2_rad(self.sdec)/math.pi

        self.ecuToalaz = EcuToHor(self.newRA, self.newDEC, self.lat, self.lon)
        (self.az,self.el) = self.ecuToalaz.getHor()

        if self.sweep == True:

            self.az = self.az - (self.tamanox / 2) + self.g*self.pasox
            self.el = self.el + (self.tamanoy / 2) - self.j*self.pasoy
            
            if self.i >= self.totalx:
                self.i = 0
                self.j = self.j + 1
                self.k = not self.k
                if self.j > self.totaly:
                    self.j = 0
                    self.g = 0
                    self.stop()
            else:
                self.i = self.i + 1
                if self.k == False:
                    self.g = self.g + 1
                else:
                    self.g = self.g - 1

        self.textEdit_11.setText('{0:.4f}'.format(self.az))
        self.textEdit_12.setText('{0:.4f}'.format(self.el))

        self.acumWord()     

    def justFirst(self):
        self.stopAuto = True
        self.frame.setEnabled(False)
        self.find = True
        self.track = False
        self.sweep = False
        self.checkBox.setChecked(True)
        self.checkBox_2.setChecked(False)
        self.checkBox_3.setChecked(False)

    def justSecond(self):
        self.timeBarrido = 1
        self.stopAuto = False
        self.frame.setEnabled(False)
        self.find = False
        self.track = True
        self.sweep = False
        self.checkBox.setChecked(False)
        self.checkBox_2.setChecked(True)
        self.checkBox_3.setChecked(False)

    def justThird(self):
        self.stopAuto = False
        self.frame.setEnabled(True)
        self.find = False
        self.track = False
        self.sweep = True
        self.checkBox.setChecked(False)
        self.checkBox_2.setChecked(False)
        self.checkBox_3.setChecked(True)

    def fromJS(self,vel,m_az,m_el):
        self.vel = vel
        self.m_az = m_az
        self.m_el = m_el
        self.acumWord()
        
    def acumWord(self):
        if self.RT != None:
            if self.ori != 1:
                self.RT.writeWord(self.az,self.el,self.m,self.vel,self.m_az,self.m_el,self.h,self.ori)
            elif self.ori == 1 and self.yaori == 1:
                self.ori = 0
                self.RT.writeWord(self.az,self.el,self.m,self.vel,self.m_az,self.m_el,self.h,self.ori)
            self.h = 0
        
    def connectSerial(self):
        portSerial = availablePorts()
        for path_RT in portSerial:
            print "Conexion exitosa con " + path_RT
            self.connectRT(path_RT)

    def connectRT(self, path_RT):
        try:
            if self.RT == None:
                self.RT = comSerial(portSerial = path_RT)
                #Recepcion de la cadena
                self.RT.readAntena.connect(self.updateData)
                self.RT.start()
        except:
            QtGui.QMessageBox.warning(self, 'Warning', "RT no conectado")
            self.RT = None
                    
    def home(self):
        self.textEdit_4.setText('0.0000000')
        self.az = 0
        
        self.h = 1
        self.acumWord()

    def unlock(self):
        self.textEdit.setDisabled(False)
        self.textEdit_4.setDisabled(False)

    def editPos(self):      
        self.az = float(self.textEdit.toPlainText())
        self.el = float(self.textEdit_4.toPlainText())
        self.textEdit.setDisabled(True)
        self.textEdit_4.setDisabled(True)

        if self.az >= 360:
            self.az = 0
            self.textEdit.setText('0')
        elif self.az < 0:
            self.az = 0
            self.textEdit.setText('0')

        if self.el > 90:
            self.el = 90
            self.textEdit_4.setText('90')
        elif self.el < 0:
            self.el = 0
            self.textEdit_4.setText('0')
            self.statusbar.showMessage("La antena no puede alcanzar elevacion menor a 0")

        self.acumWord()

    def modeEdit(self):
        if self.mode.currentIndex() == 0:
            #Se inicia el joystick
            self.JOY = joyStickControl(0.0001)
            self.JOY.start()

            #Conexion a la LCD 
            self.JOY.jSvel.connect(self.writeLCD)

            #Conexion a la matriz de LED
            self.JOY.jSmov.connect(self.writeMLED)
            self.JOY.jMove.connect(self.fromJS)

            #Funcion Modo Manual
            self.confManualMode()
            
        else:
            self.lcdNumber.display('0')                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
            
            #Finalizamos el joystick
            self.JOY.cancel()

            #Funcion Modo Automatico
            self.confAutoMode()

    def modifyPosSte(self,cmdText,lat,lon):
        try:
            if not os.path.exists('/home/marcial/.stellarium/data/user_locations.txt'):
                archivo = open('/home/marcial/.stellarium/data/user_locations.txt','a')
                archivo.write(cmdText)
                archivo.close()
                archivo = open('/home/marcial/.stellarium/data/user_locations.txt','r')
            else:
                archivo = open('/home/marcial/.stellarium/data/user_locations.txt','r')

            lineas = list(archivo)

            for i in range(len(lineas)):
                if lineas[i][0:14] == cmdText:
                    lineas[i] = cmdText + '\t\tMexico\tX\t0\t' + str(lat) + 'N\t' + str(lon) + 'E\t2144\t2\t\tEarth\n' 
            archivo.close()
            fileNew = open('/home/marcial/.stellarium/data/user_locations.txt','w')
            strToLine = ''.join(lineas)
            fileNew.write(strToLine)
            fileNew.close()
        except IOError:
            QtGui.QMessageBox.warning(self, 'Warning', "Fallo al cargar parametros iniciales")
    
    def confManualMode(self):
        self.statusbar.showMessage("Bienvenido !!! Modo Manual")

        self.toolButton.setDisabled(False)
        self.toolButton_2.setDisabled(False)
        self.toolButton_3.setDisabled(False)
        self.toolButton_4.setDisabled(False)

        self.m = 2
        self.acumWord()

    def confAutoMode(self):
        self.statusbar.showMessage("Bienvenido !!! Modo Automatico")

        self.lat = float(self.textEdit_2.toPlainText())
        self.lon = float(self.textEdit_3.toPlainText())

        self.textEdit_2.setDisabled(True)
        self.textEdit_3.setDisabled(True)

        self.toolButton.setDisabled(True)
        self.toolButton_2.setDisabled(True)
        self.toolButton_3.setDisabled(True)
        self.toolButton_4.setDisabled(True)

        self.textEdit_2.setText('{0:.5f}'.format(abs(self.lat)))
        self.textEdit_3.setText('{0:.5f}'.format(abs(self.lon)))
       
        if self.lat < 0:
            self.label_3.setText('S')
        else:
            self.label_3.setText('N')

        if self.lon < 0:
            self.label_4.setText('W')
        else:
            self.label_4.setText('E')

        if self.lat > 90:
            self.lat = 90
            self.textEdit_2.setText('90')
        elif self.lat < -90:
            self.lat = -90
            self.textEdit_2.setText('-90')

        if self.lon > 180:
            self.lon = 180
            self.textEdit_3.setText('180')
        elif self.lon < -180:
            self.lon = -180
            self.textEdit_3.setText('-180')

        #Abrir Stellarium
        self.modifyPosSte('SkyExplorer RT',str(self.lat),str(self.lon))
        os.system('./CheckStellarium')
        
        self.m = 1
        self.acumWord()
               
    def writeLCD(self,vel):
        
        stateVel = ""
        if vel < 4:
            stateVel = "Baja"
        elif vel < 8:
            stateVel = "Media"
        else:
            stateVel = "Alta"
            
        self.statusbar.showMessage("Velocidad: " + stateVel)
        self.lcdNumber.display(vel)
        self.vel = vel

    def writeMLED(self,m_az,m_el):

        stateMov = "" 
        self.clearButton()
        if m_az == 1 and m_el == 1:
            self.right_downButton()
            stateMov = "Abajo/Derecha"
        elif m_az == 1 and m_el == -1:
            self.right_upButton()
            stateMov = "Arriba/Derecha"
        elif m_az == -1 and m_el == 1:
            self.left_downButton()
            stateMov = "Abajo/Izquierda"
        elif m_az == -1 and m_el == -1:
            self.left_upButton()
            stateMov = "Arriba/Izquierda"
        elif m_az == 0 and m_el == 1:
            self.downButton()
            stateMov = "Abajo"
        elif m_az == 0 and m_el == -1:
            self.upButton()
            stateMov = "Arriba"
        elif m_az == 1 and m_el == 0:
            self.rightButton()
            stateMov = "Derecha"
        elif m_az == -1 and m_el == 0:
            self.leftButton()
            stateMov = "Izquierda"

        self.statusbar.showMessage("Movimiento: " + stateMov)
            
    def rightButton(self):
        self.qLed_1_4.setOffColour(QLed.Green);
        self.qLed_2_4.setOffColour(QLed.Green);
        self.qLed_2_5.setOffColour(QLed.Green);
        self.qLed_3_1.setOffColour(QLed.Green);
        self.qLed_3_2.setOffColour(QLed.Green);
        self.qLed_3_3.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_5.setOffColour(QLed.Green);
        self.qLed_3_6.setOffColour(QLed.Green);
        self.qLed_4_1.setOffColour(QLed.Green);
        self.qLed_4_2.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_4_6.setOffColour(QLed.Green);
        self.qLed_4_7.setOffColour(QLed.Green);
        self.qLed_7_4.setOffColour(QLed.Green);
        self.qLed_6_4.setOffColour(QLed.Green);
        self.qLed_6_5.setOffColour(QLed.Green);
        self.qLed_5_1.setOffColour(QLed.Green);
        self.qLed_5_2.setOffColour(QLed.Green);
        self.qLed_5_3.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_6.setOffColour(QLed.Green);
        self.qLed_5_7.setOffColour(QLed.Green);

    def upButton(self):
        self.qLed_1_4.setOffColour(QLed.Green);
        self.qLed_2_3.setOffColour(QLed.Green);
        self.qLed_2_4.setOffColour(QLed.Green);
        self.qLed_2_5.setOffColour(QLed.Green);
        self.qLed_3_2.setOffColour(QLed.Green);
        self.qLed_3_3.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_5.setOffColour(QLed.Green);
        self.qLed_3_6.setOffColour(QLed.Green);
        self.qLed_4_1.setOffColour(QLed.Green);
        self.qLed_4_2.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_4_6.setOffColour(QLed.Green);
        self.qLed_4_7.setOffColour(QLed.Green);
        self.qLed_5_3.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_6.setOffColour(QLed.Green);
        self.qLed_6_3.setOffColour(QLed.Green);
        self.qLed_6_4.setOffColour(QLed.Green);
        self.qLed_6_5.setOffColour(QLed.Green);
        self.qLed_7_3.setOffColour(QLed.Green);
        self.qLed_7_4.setOffColour(QLed.Green);
        self.qLed_7_5.setOffColour(QLed.Green);

    def downButton(self):
        self.qLed_7_4.setOffColour(QLed.Green);
        self.qLed_6_3.setOffColour(QLed.Green);
        self.qLed_6_4.setOffColour(QLed.Green);
        self.qLed_6_5.setOffColour(QLed.Green);
        self.qLed_5_2.setOffColour(QLed.Green);
        self.qLed_5_3.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_6.setOffColour(QLed.Green);
        self.qLed_5_7.setOffColour(QLed.Green);
        self.qLed_4_1.setOffColour(QLed.Green);
        self.qLed_4_2.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_4_6.setOffColour(QLed.Green);
        self.qLed_4_7.setOffColour(QLed.Green);
        self.qLed_3_3.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_5.setOffColour(QLed.Green);
        self.qLed_2_3.setOffColour(QLed.Green);
        self.qLed_2_4.setOffColour(QLed.Green);
        self.qLed_2_5.setOffColour(QLed.Green);
        self.qLed_1_3.setOffColour(QLed.Green);
        self.qLed_1_4.setOffColour(QLed.Green);
        self.qLed_1_5.setOffColour(QLed.Green);

    def leftButton(self):
        self.qLed_1_4.setOffColour(QLed.Green);
        self.qLed_2_3.setOffColour(QLed.Green);
        self.qLed_2_4.setOffColour(QLed.Green);
        self.qLed_3_2.setOffColour(QLed.Green);
        self.qLed_3_3.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_5.setOffColour(QLed.Green);
        self.qLed_3_6.setOffColour(QLed.Green);
        self.qLed_3_7.setOffColour(QLed.Green);
        self.qLed_4_1.setOffColour(QLed.Green);
        self.qLed_4_2.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_4_6.setOffColour(QLed.Green);
        self.qLed_4_7.setOffColour(QLed.Green);
        self.qLed_5_2.setOffColour(QLed.Green);
        self.qLed_5_3.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_6.setOffColour(QLed.Green);
        self.qLed_5_7.setOffColour(QLed.Green);
        self.qLed_5_8.setOffColour(QLed.Green);
        self.qLed_6_3.setOffColour(QLed.Green);
        self.qLed_6_4.setOffColour(QLed.Green);
        self.qLed_7_4.setOffColour(QLed.Green);

    def right_upButton(self):
        self.qLed_2_3.setOffColour(QLed.Green);
        self.qLed_2_4.setOffColour(QLed.Green);
        self.qLed_2_5.setOffColour(QLed.Green);
        self.qLed_2_6.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_5.setOffColour(QLed.Green);
        self.qLed_3_6.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_4_6.setOffColour(QLed.Green);
        self.qLed_5_2.setOffColour(QLed.Green);
        self.qLed_5_3.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_7.setOffColour(QLed.Green);
        self.qLed_6_3.setOffColour(QLed.Green);

    def left_upButton(self):
        self.qLed_2_2.setOffColour(QLed.Green);
        self.qLed_2_3.setOffColour(QLed.Green);
        self.qLed_2_4.setOffColour(QLed.Green);
        self.qLed_2_5.setOffColour(QLed.Green);
        self.qLed_3_2.setOffColour(QLed.Green);
        self.qLed_3_3.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_4_2.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_5_2.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_6.setOffColour(QLed.Green);
        self.qLed_5_7.setOffColour(QLed.Green);
        self.qLed_6_5.setOffColour(QLed.Green);

    def left_downButton(self):
        self.qLed_6_2.setOffColour(QLed.Green);
        self.qLed_6_3.setOffColour(QLed.Green);
        self.qLed_6_4.setOffColour(QLed.Green);
        self.qLed_6_5.setOffColour(QLed.Green);
        self.qLed_5_2.setOffColour(QLed.Green);
        self.qLed_5_3.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_4_2.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_3_2.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_6.setOffColour(QLed.Green);
        self.qLed_3_5.setOffColour(QLed.Green);
        self.qLed_2_5.setOffColour(QLed.Green);

    def right_downButton(self):
        self.qLed_6_3.setOffColour(QLed.Green);
        self.qLed_6_4.setOffColour(QLed.Green);
        self.qLed_6_5.setOffColour(QLed.Green);
        self.qLed_6_6.setOffColour(QLed.Green);
        self.qLed_5_4.setOffColour(QLed.Green);
        self.qLed_5_6.setOffColour(QLed.Green);
        self.qLed_5_7.setOffColour(QLed.Green);
        self.qLed_4_3.setOffColour(QLed.Green);
        self.qLed_4_4.setOffColour(QLed.Green);
        self.qLed_4_5.setOffColour(QLed.Green);
        self.qLed_4_6.setOffColour(QLed.Green);
        self.qLed_3_2.setOffColour(QLed.Green);
        self.qLed_3_3.setOffColour(QLed.Green);
        self.qLed_3_4.setOffColour(QLed.Green);
        self.qLed_3_6.setOffColour(QLed.Green);
        self.qLed_2_3.setOffColour(QLed.Green);

    def clearButton(self):
        self.qLed_1_1.setOffColour(QLed.Grey);
        self.qLed_1_2.setOffColour(QLed.Grey);
        self.qLed_1_3.setOffColour(QLed.Grey);
        self.qLed_1_4.setOffColour(QLed.Grey);
        self.qLed_1_5.setOffColour(QLed.Grey);
        self.qLed_1_6.setOffColour(QLed.Grey);
        self.qLed_1_7.setOffColour(QLed.Grey);
        self.qLed_2_1.setOffColour(QLed.Grey);
        self.qLed_2_2.setOffColour(QLed.Grey);
        self.qLed_2_3.setOffColour(QLed.Grey);
        self.qLed_2_4.setOffColour(QLed.Grey);
        self.qLed_2_5.setOffColour(QLed.Grey);
        self.qLed_2_6.setOffColour(QLed.Grey);
        self.qLed_2_7.setOffColour(QLed.Grey);
        self.qLed_3_1.setOffColour(QLed.Grey);
        self.qLed_3_2.setOffColour(QLed.Grey);
        self.qLed_3_3.setOffColour(QLed.Grey);
        self.qLed_3_4.setOffColour(QLed.Grey);
        self.qLed_3_5.setOffColour(QLed.Grey);
        self.qLed_3_6.setOffColour(QLed.Grey);
        self.qLed_3_7.setOffColour(QLed.Grey);
        self.qLed_4_1.setOffColour(QLed.Grey);
        self.qLed_4_2.setOffColour(QLed.Grey);
        self.qLed_4_3.setOffColour(QLed.Grey);
        self.qLed_4_4.setOffColour(QLed.Grey);
        self.qLed_4_5.setOffColour(QLed.Grey);
        self.qLed_4_6.setOffColour(QLed.Grey);
        self.qLed_4_7.setOffColour(QLed.Grey);
        self.qLed_5_1.setOffColour(QLed.Grey);
        self.qLed_5_2.setOffColour(QLed.Grey);
        self.qLed_5_3.setOffColour(QLed.Grey);
        self.qLed_5_4.setOffColour(QLed.Grey);
        self.qLed_5_6.setOffColour(QLed.Grey);
        self.qLed_5_7.setOffColour(QLed.Grey);
        self.qLed_5_8.setOffColour(QLed.Grey);
        self.qLed_6_1.setOffColour(QLed.Grey);
        self.qLed_6_2.setOffColour(QLed.Grey);
        self.qLed_6_3.setOffColour(QLed.Grey);
        self.qLed_6_4.setOffColour(QLed.Grey);
        self.qLed_6_5.setOffColour(QLed.Grey);
        self.qLed_6_6.setOffColour(QLed.Grey);
        self.qLed_6_7.setOffColour(QLed.Grey);
        self.qLed_7_1.setOffColour(QLed.Grey);
        self.qLed_7_2.setOffColour(QLed.Grey);
        self.qLed_7_3.setOffColour(QLed.Grey);
        self.qLed_7_4.setOffColour(QLed.Grey);
        self.qLed_7_5.setOffColour(QLed.Grey);
        self.qLed_7_6.setOffColour(QLed.Grey);
        self.qLed_7_7.setOffColour(QLed.Grey);

    #Salir
    def closeEvent(self, event):
        try:
            self.Server.close_socket()
            self.RT.cancel()
            event.accept()
        except:
            event.accept()

def main():
    app = QtGui.QApplication(sys.argv)
    form = GUIControl()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
