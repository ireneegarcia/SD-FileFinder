# -*- coding: utf-8 -*-
__author__ = 'students uneg'


########################################################################################################################
#  MASTER PROGRAM                                                                                                      #
########################################################################################################################
import sys
from PyQt4 import QtGui
from pyclass.MainWindow import MainWindow
########################################################################################################################


# Funciones ------------------------------------------------------------------------------------------------------------
def main():

    # instancio aplicacion de QT
    app = QtGui.QApplication(sys.argv)

    # instancio ventana principal
    main_window = MainWindow()

    # muestro ventana principal
    main_window.show()

    # asigno retorno de salida de programa de QT a la aplicacion de consola
    sys.exit(app.exec_())
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()