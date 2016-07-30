# -*- coding: utf-8 -*-
__author__ = 'students uneg'


########################################################################################################################
# Clase Ventana Principal                                                                                              #
########################################################################################################################
import sys
import json
import base64
import threading
import subprocess
sys.path.insert(0, "../")
import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.message
from PyQt4 import QtCore
from PyQt4.QtGui import *
from pyclass import ConfigWindow
########################################################################################################################


# Variables ------------------------------------------------------------------------------------------------------------
table_data = None
m          = None
# ----------------------------------------------------------------------------------------------------------------------


def on_recv(conn, ident, message):
    '''
    OnRecv  -->  Funcion disparadora al llegar un mensaje
    '''
    # hago un cast del string del mensaje llegado a un json
    msg = json.loads(str(message.data).replace('\'', '"'))

    # obtengo cual va a ser la posicion de la ultima fila
    rowPosition = table_data.rowCount()

    # inserto una fila en el grid
    table_data.insertRow(rowPosition)

    # asigno los valores devueltos de la busqueda a su posiciones correspondientes, HOST y FILE FOUND
    table_data.setItem(rowPosition, 0, QTableWidgetItem(msg['host']))
    table_data.setItem(rowPosition, 1, QTableWidgetItem(msg['data']))


def snakemq_listener():
    '''
    SnakeMQListener  -->  Funcion para instanciar una conexion con un host esclavo
    '''
    global m
    # instancio estructura y paqueteria de snakeMQ
    s = snakemq.link.Link()
    pktr = snakemq.packeter.Packeter(s)

    # instancio cola de mensajes con identificador MASTER
    m = snakemq.messaging.Messaging("master", "", pktr)

    # asigno evento de recepcion de mensajes a la funcion on_recv
    m.on_message_recv.add(on_recv)

    # abro archivo en modo lectura de los hosts configurados
    with open('host.txt', 'r') as f:
        # construyo mensaje de identificacion con la cadena abajo descrita
        msg = snakemq.message.Message(str('**identcmd**').encode(), ttl=60)

        # leo cada linea de archivo (que deberia ser un host)
        for line in f.readlines():
            node_host = line.replace('\n', '')

            # intento establecer conexion
            s.add_connector((node_host, 4000))

            # envio mi identificacion como MASTER
            m.send_message(node_host, msg)

    # creo el ciclo de procesamiento de colas
    s.loop()


class MainWindow(QWidget):

    def __init__(self):
        '''
        Construct  -->  Funcion constructora
        '''
        # inicio servicio de procesamiento de colas de snakeMQ
        threading.Thread(target=snakemq_listener).start()
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        '''
        Initialize User Interface  -->  Funcion instanciar la ventana principal
        '''
        self.resize(640, 480)
        self.setWindowTitle("SD_Garcia_Etcheverry -  Master")
        self.center()

        label_search = QLabel("<h4>Archivo:</h4>", self)
        label_search.move(30, 30)

        self.line_search = QLineEdit("", self)
        self.line_search.setGeometry(100, 26, 200, 25)

        button_search = QPushButton("Buscar", self)
        button_search.move(310, 25)
        button_search.clicked.connect(self.search)

        button_clear = QPushButton("Limpiar", self)
        button_clear.move(410, 25)
        button_clear.clicked.connect(self.clear)

        button_conf = QPushButton("Configuracion", self)
        button_conf.move(510, 25)
        button_conf.clicked.connect(self.configuration)

        global table_data
        table_data = QTableWidget(0, 2, self)
        table_data.setHorizontalHeaderLabels(("Host", "Direccion"))
        table_data.setGeometry(30, 75, 580, 380)
        table_data.setColumnWidth(0, 120)
        table_data.setColumnWidth(1, 419)
        table_data.doubleClicked.connect(self.browser_openfile)

        self.configuration_window = ConfigWindow.ConfigWindow()

    def center(self):
        '''
        Center  -->  Funcion para centrar la ventana
        '''
        frameGm = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def search(self):
        '''
        Search  -->  Funcion para mandar la orden del archivo a buscar a los hosts esclavos
        '''
        # instancio mensaje de archivo a buscar en los nodos esclavos
        msg = snakemq.message.Message(str(self.line_search.text()).encode(), ttl=60)

        # le envio el mensaje a la primera fila de nodos con los que este conectado
        with open('host.txt', 'r') as f:
            for line in f.readlines():
                m.send_message(line.replace('\n', ''), msg)

    @QtCore.pyqtSlot()
    def configuration(self):
        '''
        Configuration  -->  Funcion para mostrar la ventana de configuracion de hosts
        '''
        self.configuration_window.show()

    def clear(self):
        '''
        Clear  -->  Funcion para limpiar la rejilla de datos
        '''
        # asignar 0 filas al grid
        table_data.setRowCount(0)

    @QtCore.pyqtSlot()
    def browser_openfile(self):
        # obtengo la fila seleccionada del grid al que le hice doble click
        row = table_data.currentRow()

        # abro navegador web con el host y direccion de archivo para visualizar o descargar, segun sea el caso
        subprocess.call('google-chrome http://' + str(table_data.item(row, 0).text()) + ':5000/' + base64.b64encode(str(table_data.item(row, 1).text())) + ' &', shell=True)