from threading import Thread
from connection import Connection
import socket
from settings import *

class Server():
    def __init__(self, host, port):
        self.serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serv.bind((host, port))
        self.serv.listen(1) # number ?
        self.clients = {}

    def runServer(self):
        while True:
            print("Connection waiting...")
            sock, addr = self.serv.accept()
            if self.clients.has_key(addr[0]):
                client = self.clients[addr[0]]
                client.setSock(sock)
            else:
                client = Client(sock, addr)
                self.clients[addr[0]] = client

            t = Thread(target=client.worker)
            t.start()

class Client(Connection):
    def __init__(self, sock, addr):
        super(Client, self).__init__(sock, addr)
        self.expire = 1000
        self.lastId = 2
        self.addStream(self.lastId)

    def worker(self):
        data = self.recv()
        while len(data):
            self.parseData(data)
            data = self.recv()

    def setSock(self, sock):
        self.sock = sock

    def recv(self):
        return self.sock.recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8)
