from settings import *
import sys
from pyHPACK.tables import Table
from binascii import hexlify
import time
from connection import Client

table = Table()

def access(host, port):
    con = Client(host, port)
    con.setTable(table)
    con.notifyHTTP2()
    con.send(TYPE.SETTINGS, ident=SET.NO, value = "")
    con.send(TYPE.HEADERS, FLAG.NO, 1, headers = [[":method", "GET"],
                                                  [":scheme", "http"],
                                                  [":authority", "127.0.0.1"],
                                                  [":path", "/"]])

    con.send(TYPE.PUSH_PROMISE, FLAG.NO, 1, pushId = 3, headers = [[":method", "GET"],
                                                                   [":scheme", "http"],
                                                                   [":authority", "127.0.0.1"],
                                                                   [":path", "/"]])
    #con.send(TYPE.PRIORITY, FLAG.NO, 1, E = 1, depend = 1, weight = 1)
    con.send(TYPE.PING, ping = "hello!!!!!")
    con.send(TYPE.WINDOW_UPDATE, streamId = 0, windowSizeIncrement = 10, R = 1)
    con.send(TYPE.WINDOW_UPDATE, streamId = 1, windowSizeIncrement = 10, R = 1)
    con.send(TYPE.RST_STREAM, streamId = 1, err = ERR.NO_ERROR)
    con.send(TYPE.GOAWAY, err = ERR.NO_ERROR, debug = None)

    for i in range(2):
        data = con.sock.recv(1024)
        print(hexlify(data))
        con.parseData(data)
    time.sleep(1)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8080
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], sys.argv[2]

    access(host, port)
