from threading import Thread
from connection import Connection
import socket
from settings import *
import ssl

class Server():
    def __init__(self, host, port, debug = False):
        self.serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serv.bind((host, port))
        self.serv.listen(1) # number ?
        self.clients = {}
        self.debug = debug

    def runServer(self, enable_tls = False):
        while True:
            print("Connection waiting...")
            sock, addr = self.serv.accept()

            if enable_tls:
                sock = ssl.wrap_socket(sock,
                                            server_side = True,
                                            certfile = "server.crt",
                                            keyfile = "server.key",
                                            ssl_version = ssl.PROTOCOL_SSLv3)

            client = Client(sock, addr, enable_tls, self.debug)
            self.clients[addr[0]] = client

            t = Thread(target=client.worker)
            t.setDaemon(True)
            t.start()

class Client(Connection):
    def __init__(self, sock, addr, enable_tls, debug):
        super(Client, self).__init__(sock, addr, enable_tls, debug)
        self.nextStreamID = 2
        self.expire = 1000

    def worker(self):
        while self.validateData():
            pass
        else:
            pass

    def recv(self):
        return self._recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8)
