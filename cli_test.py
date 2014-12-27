from settings import *
import sys
from binascii import hexlify
import time
from client import Client
from threading import Thread

def access(host, port):
    con = Client(host, port, False, True)
    con.notifyHTTP2()
    time.sleep(0.2)
    con.send(TYPE.SETTINGS, ident=SETTINGS.NO, value = "")
    time.sleep(0.2)
    raw_input("next")
    con.send(TYPE.HEADERS, FLAG.NO, 1, headers = [[":method", "GET"],
                                                  [":scheme", "http"],
                                                  [":authority", "127.0.0.1"],
                                                  [":path", "/"]])

    raw_input("next")
    con.send(TYPE.PUSH_PROMISE, FLAG.NO, 1, pushId = 3, headers = [[":method", "GET"],
                                                                   [":scheme", "http"],
                                                                   [":authority", "127.0.0.1"],
                                                                   [":path", "/"]])
    #con.send(TYPE.PRIORITY, FLAG.NO, 1, E = 1, depend = 1, weight = 1)
    raw_input("next")
    con.send(TYPE.PING, ping = "hello!!")
    raw_input("next")
    con.send(TYPE.WINDOW_UPDATE, streamId = 0, windowSizeIncrement = 10, R = 1)
    raw_input("next")
    con.send(TYPE.WINDOW_UPDATE, streamId = 1, windowSizeIncrement = 10, R = 1)
    raw_input("next")
    con.send(TYPE.RST_STREAM, streamId = 1, err = ERR_CODE.NO_ERROR)
    raw_input("next")
    con.send(TYPE.GOAWAY, err = ERR_CODE.NO_ERROR, debug = None)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8888
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], int(sys.argv[2])

    access(host, port)
