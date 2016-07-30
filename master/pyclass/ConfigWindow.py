# -*- coding: utf-8 -*-
__author__ = 'students uneg'


########################################################################################################################
# Clase Ventana de Configuracion                                                                                       #
########################################################################################################################
import os
import subprocess
from PyQt4.QtGui import *
########################################################################################################################


class ConfigWindow(QWidget):

    def __init__(self):
        '''
        Construct  -->  Funcion constructora
        '''
        super(ConfigWindow, self).__init__()
        self.initUI()

    def initUI(self):
        '''
        Initialize User Interface  -->  Funcion instanciar la ventana principal
        '''
        self.resize(320, 240)
        self.setWindowTitle("Configuracion")
        self.center()

        label_description = QLabel("<h4>Host Esclavos:</h4>", self)
        label_description.move(20, 15)

        self.text_edit_host = QTextEdit(self)
        self.text_edit_host.setGeometry(20, 40, 280, 180)
        with open('host.txt', 'r') as f:
            for line in f.readlines():
                self.text_edit_host.append(line.replace('\n', ''))

        button_save = QPushButton("Guardar", self)
        button_save.move(220, 10)
        button_save.clicked.connect(self.hosts_save)

    def center(self):
        '''
        Center  -->  Funcion para centrar la ventana
        '''
        frameGm = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def hosts_save(self):
        '''
        HostsSave  -->  Funcion para guardar los hosts configurados
        '''
        # abro el archivo de hosts en modo escritura y escribo en el archivo lo que configure
        with open('host.txt', 'w') as f:
            f.write(self.text_edit_host.toPlainText())

        # muestro mensaje de que morira la aplicacion y debera iniciarla nuevamente
        QMessageBox.about(self, "Configuracion", "Guardada exitosamente!\nInicie la aplicacion nuevamente")

        # mato la aplicacion con signal kill forced
        subprocess.call('kill -9 ' + str(os.getpid()), shell=True)