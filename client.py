from pyHPACK.HPACK import encode
from settings import BaseFlag, FrameType, ErrorCode, Settings, CONNECTION_PREFACE
import sys
from http2 import Client
from binascii import hexlify
from pyHPACK.tables import Table
import socket

Flag = BaseFlag
Type = FrameType
table = Table()
Err = ErrorCode
Set = Settings

def access(host, port):
    con = Client(host, port)
    con.setTable(table)

    con.send(CONNECTION_PREFACE)
    con.send(con.makeFrame(Type.SETTINGS, ident=Set.NO, value=""))
    headers = [[":method", "GET"], [":scheme", "http"], [":authority", "127.0.0.1"], [":path", "/"]]
    con.setHeaders(headers)
    con.send(con.makeFrame(Type.HEADERS, Flag.END_HEADERS, 1))
    con.send(con.makeFrame(Type.PING, ping="hello"))
    con.send(con.makeFrame(Type.GOAWAY, err = Err.NO_ERROR, debug = None))

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8080
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], sys.argv[2]

    access(host, port)
