import struct
from util import *
from settings import *

def getFrame(data):
    header = Http2Header.getFrame(data[:9])

    if header.frame == TYPE.DATA:
        frame = Data.getFrame(data[9:])
    elif header.frame == TYPE.HEADERS:
        frame = Headers.getFrame(data[9:])
    elif header.frame == TYPE.PRIORITY:
        frame = Priority.getFrame(data[9:])
    elif header.frame == TYPE.RST_STREAM:
        frame = RstStream.getFrame(data[9:])
    elif header.frame == TYPE.SETTINGS:
        frame = Settings.getFrame(data[9:])
    elif header.frame == TYPE.PUSH_PROMISE:
        frame = PushPromise.getFrame(data[9:])
    elif header.frame == TYPE.PING:
        frame = Ping.getFrame(data[9:])
    elif header.frame == TYPE.GOAWAY:
        frame = Goaway.getFrame(data[9:])
    elif header.frame == TYPE.WINDOW_UPDATE:
        frame = WindowUpdate.getFrame(data[9:])
    elif header.frame == TYPE.CONTINUATION:
        frame = Continuation.getFrame(data[9:])

    header.setLength(len(frame.wire))
    frame.addHttp2Header(header)

    return frame

class Http2Header():
    def __init__(self, frame, flags, streamID, parsing):
        self.frame = frame
        self.flags = flags
        self.streamID = streamID
        if not parsing:
            self._makeWire()

    def _makeWire(self):
        self.wire = struct.pack(">I2BI", self.length, self.frame, self.flags, self.sId)[1:]

    def setLength(self, length):
        self.length = length

    def getWire(self):
        return self.wire

    @staticmethod
    def getFrame(data):
        length, frame, flags, streamID = struct.unpack(">I2BI", "\x00"+data)
        return Http2Header(length, frame, flags, streamID, True)


class Data():
    def __init__(self, data = "", padLen = 0, parsing = False):
        self.data = data
        self.padLen = padLen
        if not parsing:
            self._makeWire()

    def _makeWire(self):
        self.wire = ""
        padding = ""
        if self.header.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        self.wire += self.data + padding

    def getWire(self):
        return super(Data, self).getWire() + self.wire

    def addHeader(self, h2Header):
        self.header = h2Header

    @staticmethod
    def getFrame(data):
        index = 0
        padLen = 0
        if flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            index += 1
        content = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
        return Data(content, padLen, True)
