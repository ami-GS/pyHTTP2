from settings import *
import sys
from binascii import hexlify
import time
from client import Client
from threading import Thread
from frame import *

def access(host, port):
    con = Client((host, port), False, True)
    con.notifyHTTP2()
    time.sleep(0.2)
    con.sendFrame(Settings())
    time.sleep(0.2)
    raw_input("next")
    con.sendFrame(Headers(FLAG.END_HEADERS, 1, [[":method", "GET"],
                                                  [":scheme", "http"],
                                                  [":authority", "127.0.0.1"],
                                                  [":path", "/"]], "", con.table))
    raw_input("next")
    con.sendFrame(Push_Promise(FLAG.END_HEADERS, 1, 3, [[":method", "GET"],
                                                        [":scheme", "http"],
                                                        [":authority", "127.0.0.1"],
                                                        [":path", "/"]], "", 0, con.table))
    #con.send(TYPE.PRIORITY, FLAG.NO, 1, E = 1, depend = 1, weight = 1)
    raw_input("next")
    con.sendFrame(Ping(FLAG.NO, "HELLO!!"))
    raw_input("next")
    con.sendFrame(Window_Update(0, 10))
    raw_input("next")
    con.sendFrame(Window_Update(1, 10))
    raw_input("next")
    con.sendFrame(Rst_Stream(1, ERR_CODE.NO_ERROR))
    raw_input("next")
    con.sendFrame(Goaway(5, ERR_CODE.NO_ERROR, debugString = "debug!!"))

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8888
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], int(sys.argv[2])

    access(host, port)
