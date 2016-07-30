# -*- coding: utf-8 -*-
__author__ = 'students uneg'


########################################################################################################################
#  SLAVE PROGRAM                                                                                                       #
########################################################################################################################
import os
import re
import sys
import json
import base64
import fnmatch
import platform
import itertools
import threading
import subprocess
sys.path.insert(0, "../")
import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.message
from flask import Flask, send_file
########################################################################################################################


# Variables ------------------------------------------------------------------------------------------------------------
s              = None
m              = None
host           = None
slaves         = []
master         = False
cid_master     = None
search_folders = []
app            = Flask(__name__)
# ----------------------------------------------------------------------------------------------------------------------


# servicios web --------------------------------------------------------------------------------------------------------
@app.route('/<path:path>')
def static_file(path):
    """
    StaticFile  -->  Funcion para servir el archivo segun una ruta a traves de base 64
    """
    # decodifico el base64 para obtener la verdadera cadena que quiero procesar
    filepath = str(base64.b64decode(path)).replace('\n', '')

    # envio el archivo con la cadena decodificada
    return send_file(filepath, attachment_filename=filepath[filepath.rfind('/'):])

def webserver():
    """
    WebServer  -->  Funcion para arrancar el servidor web
    """
    try:
        # inicia servicios web, escuchando de todos lados, permitiendo conexiones remotas entrantes
        app.run(host="0.0.0.0")
    except:
        pass
# ----------------------------------------------------------------------------------------------------------------------


# Funciones ------------------------------------------------------------------------------------------------------------
def send_messages_to_idents_hosts(data_msg):
    """
    SendMessagesToIdentsHosts  -->  Funcion para enviar un mensaje a los nodos que se conectaron a mi
    """
    # instancio mensaje
    msg = snakemq.message.Message(str(data_msg).encode(), ttl=60)

    # enviar a todos los nodos que se identificaron
    for node_host in slaves:
        m.send_message(node_host, msg)


def send_messages_to_servers_hosts(msg):
    """
    SendMessagesToServersHosts  -->  Funcion para enviar un mensaje a los nodos servidores a lo que me conecto
    """
    try:
        # abrir archivo en modo lectura
        with open('servers.txt', 'r') as f:
            # obtener nodos y enviarle el mensaje
            for line in f.readlines():
                node_host = line.replace('\n', '')
                m.send_message(node_host, msg)
    except:
        pass


def get_root_folder_configuration():
    """
    GetRootFolderConfiguration  -->  Funcion para delvolver la ruta raiz de la carpeta donde se buscaran archivos
    """
    folders = []
    try:
        # abrir archivo en modo lectura
        with open('rootfolders.txt', 'r') as f:
            for line in f.readlines():
                line = line.replace('\n', '')
                # si linea leida del archivo de configurarion es una carpeta que existe en disco
                if os.path.isdir(line):
                    # agregarlo al path de carpetas permitidas para buscar
                    folders.append(line)

    except:
        pass

    # si no hay ninguna carpeta valida, agregar el root /home
    if folders.__len__() == 0:
        folders.append('/home')

    # en caso de error, retornar raiz
    return folders


def search(search_data):
    """
    Search  -->  Funcion para buscar recursivamente un archivo en el computador
    """
    global m
    global host
    global slaves
    global master

    # enviar mensaje a todos los nodos que se identicaron, para buscar de manera recursiva en todos los nodos
    send_messages_to_idents_hosts(search_data)
    print("Buscando  -->  '" + search_data + "'")

    # buscar archivo en las carpetas asignadas en la configuracion
    for root_folder in search_folders:
        # buscar archivos de manera recursiva, a partir de la raiz de esta carpeta
        for root, dirnames, filenames in os.walk(root_folder):
            # si el archivo cumple con el patron de busqueda
            for filename in fnmatch.filter(filenames, search_data):
                # construyo mensaje, indicando host y direccion de archivo encontrado
                msg = snakemq.message.Message(str({
                    'host': host,
                    'data': root + '/' + filename
                }).encode(), ttl=60)
                # si tengo el MASTER conectado a mi, le notifico a el
                if master:
                    m.send_message("master", msg)
                else:
                    # en caso contrario, replico la respuesta a los nodos servidores, para hacerle llegar la informacion al MASTER
                    send_messages_to_servers_hosts(msg)
                print("Notificando  -->  " + root + filename)


def on_recv(conn, ident, message):
    """
    OnRecv  -->  Funcion disparadora al llegar un mensaje
    """
    global master
    global slaves
    global cid_master

    # si el mensaje recibido es de MASTER, asignar valores del MASTER
    if ident == 'master':
        master = True
        cid_master = conn

    # si el mensaje es de identificacion
    if message.data == '**identcmd**':
        # si es el MASTER, mostrar mensaje
        if ident == 'master':
            print("Se ha establecido conexion con el nodo MASTER")
        else:
            # en caso contrario, es un node de busqueda el que se ha conectado
            print("Se ha conectado un nodo de busqueda  -->  ", ident)

            # agregar al arreglo de nodos identificados, es decir que se conectaron a mi
            slaves.append(ident)
    else:
        try:
            json.loads(str(message.data).replace('\'', '"'))
            msg = snakemq.message.Message(str(message.data).encode(), ttl=60)
            if master:
                m.send_message("master", msg)
            else:
                send_messages_to_servers_hosts(msg)
                send_messages_to_idents_hosts(message.data)
        except:
            threading.Thread(target=search, args=(message.data,)).start()


def on_drop(ident, message):
    """
    OnDrop  -->  Funcion disparadora al borrar un mensaje
    """
    print("message dropped", ident, message)


def s_on_disconnect(conn_id):
    """
    SOnDisconnect  -->  Funcion disparadora al desconectarse un nodo
    """
    global master
    global cid_master

    # si id de la conexion es la que tengo del master, quiere decir que se desconecto el MASTER
    if conn_id == cid_master:
        # asignar valores de perdida del MASTER
        master = False
        cid_master = None
        print('Desconectado nodo MASTER')
    else:
        # en caso contrario, fue un nodo slave cualquiera
        print('Desconectado nodo ', conn_id)


def get_ip():
    """
    GetIP  -->  Funcion para obtener el ip
    """

    # si la plataforma es windows
    if platform.system().lower() == 'windows':
        # instanciar socket y obtener ip mediante libreria
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    else:
        # en caso contrario, es linux, ejecuta el comando de mostrar la ip
        f = os.popen('ifconfig')

        # se obtiene la informacion y se procesar por expresiones regulares
        for iface in [' '.join(i) for i in iter(lambda: list(itertools.takewhile(lambda l: not l.isspace(), f)), [])]:
            if re.findall('^(eth|wlan|wlp2s)[0-9]', iface) and re.findall('RUNNING', iface):
                # caso para debian
                ip = re.findall('(?<=inet\saddr:)[0-9\.]+', iface)
                # caso para fedora
                if not ip:
                    ip = re.findall('(?<=inet\s)[0-9\.]+', iface)
                if ip:
                    return ip[0]
    return False


def send_ident(node_host):
    """
    SendIdent  -->  Funcion para enviar una identificacion a un nodo
    """
    global m

    # instancio paquete de identificacion
    msg = snakemq.message.Message(str('**identcmd**').encode(), ttl=60)

    # enviar mensaje al nodo
    m.send_message(node_host, msg)


def connect_nodes_servers_and_send_ident():
    """
    ConnectNodesAndSendIdent  -->  Funcion para conectarse con otros nodos servidores y enviarle su identificacion
    """
    try:

        # abrir archivo de servers.txt en modo lectura
        with open('servers.txt', 'r') as f:

            # recorro todas las lineas
            for line in f.readlines():

                # formateo la linea eliminando los saltos de linea, deberia ser un host
                node_host = line.replace('\n', '')
                print("Conectando  -->  ", node_host)
                try:
                    # establezco conexion con el nodo
                    s.add_connector((node_host, 4000))

                    # envio identificacion
                    send_ident(node_host)
                except:
                    pass
    except:
        pass


def main():
    global s
    global m
    global host
    global search_folders

    # obtengo ip del equipo
    host = get_ip()
    print("HOST=", host)

    # muestro la configuracion
    search_folders = get_root_folder_configuration()
    print("ROOT FOLDER=", search_folders)

    # instancia de estructura snakeMQ
    s = snakemq.link.Link()

    # asignar evento de desconexion de un nodo a la funcion s_on_disconnect
    s.on_disconnect.add(s_on_disconnect)

    # se coloca el puerto 4000  en escucha para conexion de nodos
    try:
        s.add_listener(("", 4000))
    except:
        pass

    # instancia de manejo de paquetes de snakeMQ
    pktr = snakemq.packeter.Packeter(s)

    # instancia de cola de mensajes con el identificador obtenido del ip, es decir el IP es nombre de la cola
    m = snakemq.messaging.Messaging(host, "", pktr)

    # asignar evento de recibir mensaje a on_recv, cada vez que llegue un mensaje por la cola se ejecutara ese evento
    m.on_message_recv.add(on_recv)
    m.on_message_drop.add(on_drop)

    # conectar a los nodos configurado en servers.txt y enviar identificacion de mi IP
    connect_nodes_servers_and_send_ident()

    try:
        # inicia servicio web para servir archivos
        threading.Thread(target=webserver).start()

        # inicia ciclo de procesamiento de colas de mensaje
        s.loop()
    except:

        # en caso de cerrar la aplicacion, elimina toda la aplicacion a traves de un signal kill forced
        subprocess.call('kill -9 ' + str(os.getpid()), shell=True)
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()