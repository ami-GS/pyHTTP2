import struct
from util import *
from settings import *

def getFrame(data):
    header = Http2Header.getFrame(data[:9])

    if header.frame == TYPE.DATA:
        frame = Data.getFrame(header, data[9:])
    elif header.frame == TYPE.HEADERS:
        frame = Headers.getFrame(header, data[9:])
    elif header.frame == TYPE.PRIORITY:
        frame = Priority.getFrame(header, data[9:])
    elif header.frame == TYPE.RST_STREAM:
        frame = RstStream.getFrame(header, data[9:])
    elif header.frame == TYPE.SETTINGS:
        frame = Settings.getFrame(header, data[9:])
    elif header.frame == TYPE.PUSH_PROMISE:
        frame = PushPromise.getFrame(header, data[9:])
    elif header.frame == TYPE.PING:
        frame = Ping.getFrame(header, data[9:])
    elif header.frame == TYPE.GOAWAY:
        frame = Goaway.getFrame(header, data[9:])
    elif header.frame == TYPE.WINDOW_UPDATE:
        frame = WindowUpdate.getFrame(header, data[9:])
    elif header.frame == TYPE.CONTINUATION:
        frame = Continuation.getFrame(header, data[9:])


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
    def __init__(self, flags, streamID, data = "", padLen = 0, header = None):
        self.data = data
        self.padLen = padLen
        if header:
            self.header = header
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

    @staticmethod
    def getFrame(header, data):
        index = 0
        padLen = 0
        if header.flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            index += 1
        content = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
        return Data(None, None, content, padLen, header)


class Goaway():
    def __init__(self, lastID, errorNum = ERR_CODE.NO_ERROR, debugString = "", header = None):
        self.lastID = lastID
        self.errorNum = errorNum
        self.debugString = debugString
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.GOAWAY, 0, 0)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        self.wire = packHex(self.lastID, 4)
        self.wire += packHex(self.errorNum, 4)
        self.wire += self.debugString

    @staticmethod
    def getFrame(header, data):
        lastID, errorNum = struct.unpack(">2I", data[:8])
        R = lastID >> 31
        lastID &= 0x7fffffff
        debugString = upackHex(data[8:])
        return Goaway(lastID, errorNum, debugString, header)
