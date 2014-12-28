from connection import Connection
from threading import Thread
import socket
from settings import *
import ssl

class Client(Connection):
    def __init__(self, addr, enable_tls = False, debug = False):
        if enable_tls:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = ssl.wrap_socket(self.sock)
            self.sock.connect(addr)
        else:
            self.sock = socket.create_connection(addr, 5)
        super(Client, self).__init__(self.sock, addr, enable_tls, debug)
        self.lastId = 1
        self.addStream(self.lastId)
        self.t = Thread(target=self.__receiver)
        self.t.start()

    def notifyHTTP2(self):
        self._send(CONNECTION_PREFACE)

    def __receiver(self):
        try:
            while True:
                data = self._recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8)
                self.parseData(data)
        except Exception as e:
            return
