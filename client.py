from pyHPACK.HPACK import encode
from settings import BaseFlag, CONNECTION_PREFACE
import sys
import http2
from binascii import hexlify
from pyHPACK.tables import Table
import socket

Flag = BaseFlag()
table = Table()
sock = None

def access(host, port):
    global sock
    if not sock:
        sock = socket.create_connection((host, port), 5)
        sock.send(CONNECTION_PREFACE)
        print(hexlify(sock.recv(128)))
    sock.send(http2.SettingsFrame())
    print(hexlify(sock.recv(128)))
    headers = [[":method", "GET"], [":scheme", "http"], [":authority", "127.0.0.1"], [":path", "/"]]
    sock.send(http2.HeadersFrame(Flag.NO, headers, 1, table))
    sock.send(http2.GoAwayFrame(1))
    a = sock.recv(256)
    #print(hexlify(a))
    print(a)

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8080
    
    if len(sys.argv) == 3:
        host, port = sys.argv[1], sys.argv[2]

    access(host, port)
