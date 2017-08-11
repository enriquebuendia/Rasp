#!/usr/bin/python
# -*- coding: utf-8 -*-
 
import math
import logging
from PyQt4 import QtCore
import asyncore, socket
from time import sleep, time
from string import replace
from bitstring import BitArray, BitStream, ConstBitStream
import coords
 
logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(funcName)s - %(levelname)s: %(message)s")
 
## \brief Implementación de la parte del servidor para el 'Stellarium Telescope Protocol'.
#
#  Establece la ejecución de un hilo independiente para gestionar las comunicaciones con el lado del 
#  cliente (programa Stellarium).
class Telescope_Channel(QtCore.QThread, asyncore.dispatcher):
 
    ## Constructor de la clase.
    #
    # \param conn_sock Socket de la conexión establecida con el cliente.
    def __init__(self, conn_sock):
        self.is_writable = False
        self.buffer = ''
        asyncore.dispatcher.__init__(self, conn_sock)
        QtCore.QThread.__init__(self, None)
 
    ## Indica si ya se puede leer del socket.
    #
    # \return Booleano True/False.
    def readable(self):
        return True
 
    ## Indica si el socket está disponible para escribir en él.
    #
    # \return Booleano True/False.
    def writable(self):
        return self.is_writable
 
    ## Manejador para el evento de cierre de la conexión.
    def handle_close(self):
        logging.debug("Desconectado")
        self.close()
 
    ## Manejador para la lectura del socket.
    #    
    #  Lee los datos recibidos por el socket desde el cliente, los procesa para obtener las coordenadas
    #  en el formato adecuado y los imprime por consola.
    def handle_read(self):
        #formato: 20 bytes en total.
        #Los mensajes entrantes vienen con 160 bytes..
        data0 = self.recv(160);
        if data0:            
            data = ConstBitStream(bytes=data0, length=160)
            #print "Recibido (binario): %s" % data.bin
 
            msize = data.read('intle:16')
            mtype = data.read('intle:16')
            mtime = data.read('intle:64')
 
            # RA: 
            ant_pos = data.bitpos
            ra = data.read('hex:32')
            data.bitpos = ant_pos
            ra_uint = data.read('uintle:32')
 
            # DEC:
            ant_pos = data.bitpos
            dec = data.read('hex:32')
            data.bitpos = ant_pos
            dec_int = data.read('intle:32')
 
            logging.debug("Size: %d, Type: %d, Time: %d, RA: %d (%s), DEC: %d (%s)" % (msize, mtype, mtime, ra_uint, ra, dec_int, dec))
            (sra, sdec, stime) = coords.eCoords2str(float("%f" % ra_uint), float("%f" % dec_int), float("%f" %  mtime))
 
            #Enviando de nuevo las coordenadas a Stellarium
            self.act_pos(coords.hourStr_2_rad(sra), coords.degStr_2_rad(sdec))
 
    ## Método que actualiza en Stellarium la posición del visor en pantalla.
    #
    #  Recibe las coordenadas y las vuelve a enviar hacia Stellarium a través del método 'move' de la clase.
    #
    # \param ra Ascensión recta.
    # \param dec Declinación.
    def act_pos(self, ra, dec):
        (ra_p, dec_p) = coords.rad_2_stellarium_protocol(ra, dec)
 
        times = 10 #Número de veces que Stellarium espera recibir las coordenadas //Absolutamente empírico...
        for i in range(times):
            self.move(ra_p, dec_p)
 
    ## Método que envía a Stellarium las coordenadas ecuatoriales para actualizar la posición del visor en pantalla.
    #
    #  Recibe las coordenadas en formato float, las transforma al formato del protocolo y las envía al cliente (Stellarium).
    #  Obtiene el timestamp de la medida a partir de la hora local.
    #
    # \param ra Ascensión recta.
    # \param dec Declinación.
    def move(self, ra, dec):
        msize = '0x1800'
        mtype = '0x0000'
        localtime = ConstBitStream(replace('int:64=%r' % time(), '.', ''))
        #print "move: (%d, %d)" % (ra, dec)
 
        sdata = ConstBitStream(msize) + ConstBitStream(mtype)
        sdata += ConstBitStream(intle=localtime.intle, length=64) + ConstBitStream(uintle=ra, length=32)
        sdata += ConstBitStream(intle=dec, length=32) + ConstBitStream(intle=0, length=32)
        self.buffer = sdata
        self.is_writable = True
        self.handle_write()
 
    ## Manejador del envío de datos a través del socket.
    def handle_write(self):
        self.send(self.buffer.bytes)
        self.is_writable = False
 
## \brief Implementación de la parte del servidor para el 'Stellarium Telescope Protocol'.
#
#  Establece la ejecución de un hilo independiente para gestionar las peticiones de conexión desde el 
#  cliente (programa Stellarium).
#  Por cada conexión, ejecuta un nuevo hilo que gestionará las comunicaciones (Telescope_Channel).
class Telescope_Server(QtCore.QThread, asyncore.dispatcher):
 
    ## Constructor de la clase.
    #
    # \param port Puerto en el que se pondrá a la escucha.
    def __init__(self, port=10001):
        asyncore.dispatcher.__init__(self, None)
        QtCore.QThread.__init__(self, None)
        self.tel = None
        self.port = port
 
    ## Comienza la ejecución del hilo.
    #
    #  Pone a la escucha el socket por el puerto indicado en un hilo de ejecución independiente.
    def run(self):
        logging.info(self.__class__.__name__+" disponible.")
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('localhost', self.port))
        self.listen(1)
        self.connected = False
        asyncore.loop()
 
    ## Manejador del evento de petición de conexión.
    #
    #  Inicia un nuevo hilo con una instancia de Telescope_Channel, pasándole como parámetro el socket abierto.
    def handle_accept(self):
        self.conn, self.addr = self.accept()
        logging.debug('Conectado: %s', self.addr)
        self.connected = True
        self.tel = Telescope_Channel(self.conn)
 
    ## Cierra la conexión, si estuviera establecida.
    def close_socket(self):
        if self.connected:
            self.conn.close()
 
#Inicia un "Telescope Server"
if __name__ == '__main__':
    try:
        Server = Telescope_Server()
        Server.run()
    except KeyboardInterrupt:
        logging.debug("\nBye!")