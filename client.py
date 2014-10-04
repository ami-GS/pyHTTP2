from pyHPACK.HPACK import encode
from settings import BaseFlag, FrameType, CONNECTION_PREFACE
import sys
from http2 import Connection
from binascii import hexlify
from pyHPACK.tables import Table
import socket

Flag = BaseFlag
Type = FrameType
table = Table()
sock = None

def access(host, port):
    global sock
    con = Connection()
    con.setTable(table)

    if not sock:
        sock = socket.create_connection((host, port), 5)
        sock.send(CONNECTION_PREFACE)
        print(hexlify(sock.recv(128)))
    sock.send(con.makeFrame(Type.SETTINGS, Flag.NO, 0))
    print(hexlify(sock.recv(128)))
    headers = [[":method", "GET"], [":scheme", "http"], [":authority", "127.0.0.1"], [":path", "/"]]
    con.setHeaders(headers)
    h = con.makeFrame(Type.HEADERS, Flag.END_HEADERS, 1)
    sock.send(con.makeFrame(Type.HEADERS, Flag.END_HEADERS, 1))
    sock.send(con.makeFrame(Type.PING, Flag.NO, 0))
    sock.send(con.makeFrame(Type.GOAWAY, Flag.NO, 1))

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8080
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], sys.argv[2]

    access(host, port)
