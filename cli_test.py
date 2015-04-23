from settings import *
import sys
import time
from client import Client
from threading import Thread
from frame import *

def access(host, port):
    con = Client((host, port), False, True)
    con.notifyHTTP2()
    time.sleep(0.2)
    con.sendFrame(Settings(SETTINGS.ENABLE_PUSH, 1))
    time.sleep(0.2)
    raw_input("next")
    con.sendFrame(Headers([[":method", "GET"], [":scheme", "http"],
                           [":authority", "127.0.0.1"], [":path", "/"]],
                          1, flags=FLAG.END_HEADERS))
    raw_input("next")
    con.sendFrame(Ping("HELLO!"))
    raw_input("next")
    con.sendFrame(Window_Update(0, 10))
    raw_input("next")
    con.sendFrame(Window_Update(1, 10))
    raw_input("next")
    con.sendFrame(Rst_Stream(1))
    raw_input("next")
    con.sendFrame(Goaway(5, debugString = "debug!!"))

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8888
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], int(sys.argv[2])

    access(host, port)
