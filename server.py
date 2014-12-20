from threading import Thread
from connection import Connection
import socket
from settings import *
import ssl

class Server():
    def __init__(self, host, port):
        self.serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serv.bind((host, port))
        self.serv.listen(1) # number ?
        self.clients = {}

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

            if self.clients.has_key(addr[0]):
                client = self.clients[addr[0]]
                client.setSocket(sock, enable_tls)
            else:
                client = Client(sock, addr, enable_tls)
                self.clients[addr[0]] = client

            t = Thread(target=client.worker)
            t.start()

class Client(Connection):
    def __init__(self, sock, addr, enable_tls):
        super(Client, self).__init__(sock, addr, enable_tls)
        self.expire = 1000
        self.lastId = 2
        self.addStream(self.lastId)

    def worker(self):
        data = self.recv()
        while len(data):
            self.parseData(data)
            data = self.recv()

    def recv(self):
        return self._recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8)
