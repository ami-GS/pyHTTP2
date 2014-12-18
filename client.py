from connection import Connection
from threading import Thread
import socket
from settings import *

class Client(Connection):
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), 5)
        super(Client, self).__init__(self.sock, (host, port))
        self.lastId = 1
        self.addStream(self.lastId)
        self.t = Thread(target=self.__receiver)
        self.t.start()

    def notifyHTTP2(self):
        self.sock.send(CONNECTION_PREFACE)

    def __receiver(self):
        try:
            while True:
                data = self.sock.recv(1024)
                self.parseData(data)
        except Exception as e:
            return
