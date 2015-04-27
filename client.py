from connection import Connection
from threading import Thread
import socket
from settings import *
import ssl
from frame import *
from urlparse import urlparse

class Client(Connection):
    def __init__(self, addr, enable_tls = False, debug = False):
        if enable_tls:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = ssl.wrap_socket(self.sock)
            self.sock.connect(addr)
        else:
            self.sock = socket.create_connection(addr, 5)
        super(Client, self).__init__(self.sock, addr, enable_tls, debug, True)
        self.nextStreamID = 1
        self.t = Thread(target=self.__receiver)
        self.t.setDaemon(True)
        self.t.start()

    def notifyHTTP2(self):
        self._send(CONNECTION_PREFACE)

    def GET(self, url):
        o = urlparse(url)
        headers = [[":method", "GET"], [":scheme", o.scheme],
                   [":authority", o.hostname], [":path", o.path]]
        self.addStream(self.nextStreamID)
        self.sendFrame(Headers(headers, self.nextStreamID, flags=FLAG.END_HEADERS))
        self.nextStreamID += 2

    def __receiver(self):
        try:
            while self.validateData():
                pass
            else:
                pass

        except Exception as e:
            return
