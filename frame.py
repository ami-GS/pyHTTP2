import struct
from util import *
from settings import *

def getFrame(data):
    #length, frameType, flgas, streamID = Http2Header.parse(data[:9])

    if frameType == TYPE.DATA:
        frame = Data.getFrame(data)
    elif frameType == TYPE.HEADERS:
        frame = Headers.getFrame(data)
    elif frameType == TYPE.PRIORITY:
        frame = Priority.getFrame(data)
    elif frameType == TYPE.RST_STREAM:
        frame = RstStream.getFrame(data)
    elif frameType == TYPE.SETTINGS:
        frame = Settings.getFrame(data)
    elif frameType == TYPE.PUSH_PROMISE:
        frame = PushPromise.getFrame(data)
    elif frameType == TYPE.PING:
        frame = Ping.getFrame(data)
    elif frameType == TYPE.GOAWAY:
        frame = Goaway.getFrame(data)
    elif frameType == TYPE.WINDOW_UPDATE:
        frame = WindowUpdate.getFrame(data)
    elif frameType == TYPE.CONTINUATION:
        frame = Continuation.getFrame(data)

        

    return frame

class Http2Header():
    def __init__(self, frame, flags, streamID, parsing):
        #self.length = length
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
    def __init__(self, data = "", padLen = 0, flags = "", streamID = -1,  h2Header = None):
        self.data = data
        self.padLen = padLen
        if h2Header:
            self.header = h2Header
        else:
            self.header = Http2Header(TYPE.DATA, flags, streamID)
            self._makeWire()
        self.header.setLength(len(self.wire))

    def _makeWire(self):
        self.wire = ""
        padding = ""
        if self.header.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        self.wire += self.data + padding

    def getWire(self):
        return super(Data, self).getWire() + self.wire

    @staticmethod
    def getFrame(data):
        headerFrame =  Http2Header.getFrame(data[:9])
        data = data[9:]
        index = 0
        padLen = 0
        if flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            index += 1
        content = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
        return Data(content, padLen, h2Header = headerFrame)
