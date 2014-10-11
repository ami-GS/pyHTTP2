from http2 import Server
from pyHPACK.tables import Table
import socket
import sys

table = Table()

def runServer(host, port):
    con = Server(host, port)
    con.setTable(table) 
    con.runServer()


if __name__ == "__main__":
    args = sys.argv
    host = "127.0.0.1"
    port = 8080

    if len(args) == 3:
        host = args[1]
        port = args[2]

    runServer(host, port)
