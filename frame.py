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
    def __init__(self, frame, flags, streamID, parsing = False):
        self.frame = frame
        self.flags = flags
        self.streamID = streamID
        if not parsing:
            self._makeWire()

    def _makeWire(self):
        self.wire = struct.pack(">I2BI", self.length, self.frame, self.flags, self.streamID)[1:]

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



class Headers():
    def __init__(self, flags, streamID, headers, padLen = 0, E = 0, streamDependency = 0, weight = 0, table = None, header = None):
        self.headers = headers
        self.padLen = padLen
        self.E = E
        self.streamDependency = streamDependency
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.HEADERS, flgas, streamID)
            self._makeWire(table)
            self.header.setLength(len(self.wire))

    def _makeWire(self, table):
        padding = ""
        self.wire = encode(headers, False, False, False, table)
        if self.header.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        if self.header.flags&FLAG.PRIORITY == FLAG.PRIORITY:
            if self.E:
                self.wire += packHex(self.streamDependency | 0x80000000, 4)
            else:
                self.wire += packHex(self.streamDependency, 4)
            self.wire += packHex(self.weight, 1)
        if self.header.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            #set state half closed local
            pass
        if self.header.flags&FLAG.END_STREAM == FLAG.END_STREAM:
            #set state half closed local
            pass
        self.wire += padding

    @staticmethod
    def getFrame(header, data, table):
        if header.streamID == 0:
            #send error here?
            pass

        index = 0
        padLen = 0
        E = 0
        streamDependency = 0
        weight = 0
        if header.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            headers = decode(data, table)
            #return DATA
        if header.flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct,unpack(">B", data[0])[0]
            padding = data[-padLen:]
            index += 1
        if header.flags&FLAG.PRIORITY == FLAG.PRIORITY:
            streamDependency, weight = struct.unpack(">IB", data[index:index+5])
            E = streamDependenct >> 31
            streamDependency &= 0x7fffffff
            index += 5
        if header.flags&FLAG.END_STREAM == FLAG.END_STREAM:
            #set state half closed remote
            pass

        #append wire if not a END_HEADERS flag
        return Headers(None, None, headers, padLen, E, streamDependency, weight, None, header)


class Priority():
    def __init__(self, streamID, E = 0, streamDependency = 0, weight = 0, header = None):
        self.E = E
        self.streamDependency = streamDependency
        self.weight = self.weight
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.PRIORITY, 0, streamID)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        if self.E:
            self.wire = packHex(self.streamDependency | 0x80000000, 4)
        else:
            self.wire = packHex(self.streamDependency, 4)
        self.wire += packHex(self.weight, 1)

    @staticmethod
    def getFrame(header, data):
        if header.length != 5:
            #frame_size_error
            pass
        streamDependency, weight = struct.unpack(">IB", data[:5])
        E = streamDependency >> 31
        streamDependency &= 0x7fffffff
        return Priority(None, E, streamDependency, weight, header)

class Rst_stream():
    def __init__(self, streamID, errorNum = ERR_CODE.NO_ERROR, header = None):
        self.errorNum = errorNum
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.RST_STREAM, 0, streamID)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        self.wire = packHex(self.errorNum, 4)

    @staticmethod
    def getFrame(header, data):
        errorCode = struct.unpack(">I", data)[0]
        return Rst_stream(None, errorCode, header)


class Settings():
    def __init__(self, flags, settingID = SETTINGS.NO, value = 0, header = None):
        self.settingID = settingID
        self.value = value
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.SETTINGS, flags, 0)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        if self.header.flags & FLAG.ACK == FLAG.ACK:
            self.wire = ""
            return
        self.wire = packHex(self.settingID, 2) + packHex(self.value, 4)

    @staticmethod
    def getFrame(header, data):
        settingID, value = struct.unpack(">HI", data[:6])
        return Settings(None, settingID, value, header)


class Push_primise():
    def __init__(self, flags, streamID, promisedID, padLen = 0, headers = None, table = None,  header = None):
        self.promisedID = promisedID
        self.padLen = padLen
        self.headers = headers
        if headr:
            self.header = header
        else:
            self.header = Http2Header(TYPE.PUSH_PROMISE, flgas, streamID)
            self._makeWire(table)
            self.header.setLength(len(self.wire))

    def _makeWire(self, table):
        self.wire = ""
        padding = ""
        if self.header.flags & FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding = packHex(0, self.padLen)
        self.wire += packHex(self.promisedID, 4)
        if self.headers:
            self.wire += encode(self.headers, False, False, False, table)
        self.wire += padding

    @staticmethod
    def getFrame(header, data, table):
        index = 0
        padLen = 0
        if header.flags & FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            padding = data[-padlen:]
            index += 1
        promisedID = struct.unpack(">I", data[index:index+4])[0] & 0x7fffffff

        headers = None
        if header.flags & FLAG.END_HEADERS == FLAG.END_HEADERS:
            tmp = data[index+4: len(data) if header.flags & FLAG.PADDED != FLAG.PADDED else -padLen]
            headers = decode(tmp, table)
        else:
            #TODO buffer temporal header flagment
            pass

        return Push_promise(None, None, promisedID, padLen, headers, None, header)


class Ping():
    def __init__(self, flags, data, header = None):
        self.data = data
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.PING, flags, 0)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        self.wire = packHex(self.data, 8)

    @staticmethod
    def getFrame(header, data):
        return Ping(None, data[:8], header)

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

class Window_Update():
    def __init__(self, streamID, windowSizeIncrement, header = None):
        self.windowSizeIncrement = windowSizeIncrement & 0x7fffffff
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.GOAWAY, 0, streamID)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        self.wire = packHex(self.windowSizeIncrement, 4)

    @staticmethod
    def getFrame(header, data):
        windowSizeIncrement = struct.unpack(">I", data[:4])[0] & 0x7fffffff
        return Window_Update(None, windowSizeIncrement, header)

class Continuation():
    def __init__(self, flags, streamID, headerFragment, header):
        self.headerFragment = headerFragment
        if header:
            self.header = header
        else:
            self.header = Http2Header(TYPE.CONTINUATION, flags, streamID)
            self._makeWire()
            self.header.setLength(len(self.wire))

    def _makeWire(self):
        self.wire = self.headerFragment

    @staticmethod
    def getFrame(header, data):
        headerFragment = data #dangerous?
        return Continuation(None, None, headerFragment, header)
