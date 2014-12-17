from settings import *
import sys
from pyHPACK.tables import Table
from binascii import hexlify
import time
from connection import Client
from threading import Thread

table = Table()

def recv(con):
    try:
        while True:
            data = con.sock.recv(1024)
            con.parseData(data)
    except Exception as e:
        return

def access(host, port):
    con = Client(host, port)
    t = Thread(target=recv, args = (con,))
    t.start()
    con.setTable(table)
    con.notifyHTTP2()
    time.sleep(0.2)
    con.send(TYPE.SETTINGS, ident=SET.NO, value = "")
    time.sleep(0.2)
    con.send(TYPE.HEADERS, FLAG.NO, 1, headers = [[":method", "GET"],
                                                  [":scheme", "http"],
                                                  [":authority", "127.0.0.1"],
                                                  [":path", "/"]])

    time.sleep(0.2)
    con.send(TYPE.PUSH_PROMISE, FLAG.NO, 1, pushId = 3, headers = [[":method", "GET"],
                                                                   [":scheme", "http"],
                                                                   [":authority", "127.0.0.1"],
                                                                   [":path", "/"]])
    #con.send(TYPE.PRIORITY, FLAG.NO, 1, E = 1, depend = 1, weight = 1)
    time.sleep(0.2)
    con.send(TYPE.PING, ping = "hello!!")
    time.sleep(0.2)
    con.send(TYPE.WINDOW_UPDATE, streamId = 0, windowSizeIncrement = 10, R = 1)
    time.sleep(0.2)
    con.send(TYPE.WINDOW_UPDATE, streamId = 1, windowSizeIncrement = 10, R = 1)
    time.sleep(0.2)
    con.send(TYPE.RST_STREAM, streamId = 1, err = ERR.NO_ERROR)
    time.sleep(0.2)
    con.send(TYPE.GOAWAY, err = ERR.NO_ERROR, debug = None)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8888
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], int(sys.argv[2])

    access(host, port)
