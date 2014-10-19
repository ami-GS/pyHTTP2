from settings import *
from Stream import Stream
import socket

SET = Settings

class Connection():
    def __init__(self):
        self.t = ""
        self.con = None
        self.streams = [Stream(0)] # for future type
        self.enablePush = SET.INIT_VALUE[2]
        self.maxConcurrentStreams = SET.INIT_VALUE[3]
        self.maxFrameSize = SET.INIT_VALUE[5]
        self.maxHeaderListSize = SET.INIT_VALUE[6]

    def send(self, stream_id):
        pass
        # TODO: use makeFrame with stream_id

    def setTable(self, table):
        self.table = table

    def setHeaders(self, headers):
        self.headers = headers

    def addStream(self, stream):
        self.streams.append(stream)
