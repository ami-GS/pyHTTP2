from http2 import Connection
from pyHPACK.tables import Table
import socket
import sys

talbe = Table()

def runServer(host, port):
    con = Connection(host, port, "server")
    con.setTable(table) 
    con.runServer()


if __name__ == "__main__":
    args = sys.argv
    host = "127.0.0.1"
    port = 80

    if len(args) == 3:
        host = args[1]
        port = args[2]

    runServer(host, port)
