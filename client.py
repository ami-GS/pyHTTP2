from connection import Connection
from threading import Thread
import socket
from settings import *
import ssl

class Client(Connection):
    def __init__(self, host, port, enable_tls = False):
        if enable_tls:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = ssl.wrap_socket(self.sock)
            self.sock.connect((host, port))
        else:
            self.sock = socket.create_connection((host, port), 5)
        super(Client, self).__init__(self.sock, (host, port), enable_tls)
        self.lastId = 1
        self.addStream(self.lastId)
        self.t = Thread(target=self.__receiver)
        self.t.start()

    def notifyHTTP2(self):
        self._send(CONNECTION_PREFACE)

    def __receiver(self):
        try:
            while True:
                data = self._recv(1024)
                self.parseData(data)
        except Exception as e:
            return
