import struct
from util import *
from settings import *
from pyHPACK import HPACK

def getFrame(data):
    length, frameType, flags, streamID = Http2Header.getHeaderInfo(data[:9])

    if frameType == TYPE.DATA:
        frame = Data.getFrame(flags, streamID, data)
    elif frameType == TYPE.HEADERS:
        frame = Headers.getFrame(flags, streamID, data)
    elif frameType == TYPE.PRIORITY:
        frame = Priority.getFrame(flags, streamID, data)
    elif frameType == TYPE.RST_STREAM:
        frame = Rst_Stream.getFrame(flags, streamID, data)
    elif frameType == TYPE.SETTINGS:
        frame = Settings.getFrame(flags, streamID, data)
    elif frameType == TYPE.PUSH_PROMISE:
        frame = Push_Promise.getFrame(flags, streamID, data)
    elif frameType == TYPE.PING:
        frame = Ping.getFrame(flags, streamID, data)
    elif frameType == TYPE.GOAWAY:
        frame = Goaway.getFrame(flags, streamID, data)
    elif frameType == TYPE.WINDOW_UPDATE:
        frame = WindowUpdate.getFrame(flags, streamID, data)
    elif frameType == TYPE.CONTINUATION:
        frame = Continuation.getFrame(flags, streamID, data)

    return frame

class Http2Header(object):
    def __init__(self, frame, flags, streamID, length):
        self.frame = frame
        self.flags = flags
        self.streamID = streamID
        self.length = length
        self.wire = ""
        self.headerWire = ""

    def _makeHeaderWire(self):
        self.length = len(self.wire)
        self.headerWire = struct.pack(">I2BI", self.length, self.frame, self.flags, self.streamID)[1:]

    def setLength(self, length):
        self.length = length

    def getWire(self):
        return self.headerWire + self.wire

    @staticmethod
    def getHeaderInfo(data):
        length, frame, flags, streamID = struct.unpack(">I2BI", "\x00"+data)
        return length, frame, flags, streamID


class Data(Http2Header):
    def __init__(self, flags, streamID, data = "", padLen = 0, wire = ""):
        super(Data, self).__init__(TYPE.DATA, flags, streamID, len(wire[9:]))
        self.data = data
        self.padLen = padLen
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        padding = ""
        if self.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        self.wire += self.data + padding

    @staticmethod
    def getFrame(flags, streamID, data):
        targetData = data[9:]
        index = 0
        padLen = 0
        if flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", targetData[0])[0]
            index += 1
        content = targetData[index: len(targetData) if flags != FLAG.PADDED else -padLen]
        return Data(flags, streamID, content, padLen, data)


    def validate(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        state = conn.getStreamState(self.streamID)
        if state == STATE.CLOSED:
            conn.sendFrame(Rst_Stream(self.streamID, ERR_CODE.PROTOCOL_ERROR))
        if state != STATE.OPEN and state != STATE.HCLOSED_L:
            conn.sendFrame(Rst_Stream(self.streamID, ERR_CODE.STREAM_CLOSED))
        if self.Flags&FLAG.PADDED == FLAG.PADDED and self.padLen > (len(self.wire)-1):
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))

class Headers(Http2Header):
    def __init__(self, flags, streamID, headers, table = None, padLen = 0, E = 0, streamDependency = 0, weight = 0, wire = ""):
        super(Headers, self).__init__(TYPE.HEADERS, flags, streamID, len(wire[9:]))
        self.headers = headers
        self.padLen = padLen
        self.E = E
        self.streamDependency = streamDependency
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire(table)
            self._makeHeaderWire()

    def _makeWire(self, table):
        padding = ""
        self.wire = HPACK.encode(self.headers, False, False, False, table)
        if self.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        if self.flags&FLAG.PRIORITY == FLAG.PRIORITY:
            if self.E:
                self.wire += packHex(self.streamDependency | 0x80000000, 4)
            else:
                self.wire += packHex(self.streamDependency, 4)
            self.wire += packHex(self.weight, 1)
        self.wire += padding

    @staticmethod
    def getFrame(flags, streamID, data, table):
        targetData = data[9:]
        index = 0
        padLen = 0
        E = 0
        streamDependency = 0
        weight = 0
        headers = []
        if flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct,unpack(">B", targetData[0])[0]
            padding = targetData[-padLen:]
            index += 1
        if flags&FLAG.PRIORITY == FLAG.PRIORITY:
            streamDependency, weight = struct.unpack(">IB", targetData[index:index+5])
            E = streamDependenct >> 31
            streamDependency &= 0x7fffffff
            index += 5
        headerFlagment = targetData[index:-padLen]
        if flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            headers = HPACK.decode(headerFlagment, table)
            #return DATA

        #append wire if not a END_HEADERS flag
        return Headers(flags, streamID, headers, None, padLen, E, streamDependency, weight, data)

        def validate(self, conn):
            state = conn.getStreamState(self.streamID)
            if state == STATE.RESERVED_R:
                conn.setStreamState(self.streamID, STATE.HCLOSED_L)
            else:
                conn.setStreamState(self.streamID, STATE.OPEN)
            if self.streamID == 0:
                conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
            if self.Flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
                conn.sendFrame(Data(FLAG.END_STREAM, self.streamID, "return Data!"))
            if self.Flags&FLAG.END_STREAM == FLAG.END_STREAM:
                conn.setStreamState(self.streamID, STATE.HCLOSED_R)


class Priority(Http2Header):
    def __init__(self, streamID, E = 0, streamDependency = 0, weight = 0, flags = FLAG.NO, wire = ""):
        super(Priority, self).__init__(TYPE.PRIORITY, flags, streamID, len(wire[9:]))
        self.E = E
        self.streamDependency = streamDependency
        self.weight = self.weight
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        if self.E:
            self.wire = packHex(self.streamDependency | 0x80000000, 4)
        else:
            self.wire = packHex(self.streamDependency, 4)
        self.wire += packHex(self.weight, 1)

    @staticmethod
    def getFrame(flags, streamID, data):
        targetData = data[9:]
        streamDependency, weight = struct.unpack(">IB", targetData[:5])
        E = streamDependency >> 31
        streamDependency &= 0x7fffffff
        return Priority(streamID, E, streamDependency, weight, flags, data)

    def validate(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        if self.Length != 5:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FRAME_SIZE_ERROR))

class Rst_Stream(Http2Header):
    def __init__(self, streamID, errorNum = ERR_CODE.NO_ERROR, flags = FLAG.NO, wire = ""):
        super(Rst_Stream, self).__init__(TYPE.RST_STREAM, flags, streamID, len(wire[9:]))
        self.errorNum = errorNum
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = packHex(self.errorNum, 4)

    @staticmethod
    def getFrame(flags, streamID, data):
        errorCode = struct.unpack(">I", data[9:])[0]
        return Rst_Stream(streamID, errorCode, flags, data)

    def validate(self, conn):
        if self.Length != 4:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FRAME_SIZE_ERROR))
        if self.streamID == 0 or conn.getStreamState(self.streamID) == STATE.IDLE:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        else:
            conn.setStreamState(self.streamID, STATE.CLOSED)

class Settings(Http2Header):
    def __init__(self, flags, settingID = SETTINGS.NO, value = 0, streamID = 0, wire = ""):
        super(Settings, self).__init__(TYPE.SETTINGS, flags, streamID, len(wire[9:]))
        self.settingID = settingID
        self.value = value
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        if self.flags & FLAG.ACK == FLAG.ACK:
            self.wire = ""
            return
        self.wire = packHex(self.settingID, 2) + packHex(self.value, 4)

    @staticmethod
    def getFrame(flags, streamID, data):
        settingID, value = struct.unpack(">HI", data[:6])
        return Settings(flags, settingID, value, streamID, data)

    def validate(self, conn):
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        if self.Length % 6 != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FRAME_SIZE_ERROR))
        if self.Flags&FLAG.ACK == FLAG.ACK:
            if self.Length != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FRAME_SIZE_ERROR))
        elif self.Length:
            if self.settingID == SETTINGS.HEADER_TABLE_SIZE:
                conn.setHeaderTableSize(self.value)
            elif self.settingID == SETTINGS.ENABLE_PUSH:
                if self.value == 1 or value == 0:
                    conn.enablePush = value
                else:
                    conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
            elif self.settingID == SETTINGS.MAX_CONCURRENT_STREAMS:
                if self.value <= 100:
                    print("Warnnig: max_concurrent_stream below 100 is not recomended")
                conn.maxConcurrentStreams = self.value
            elif self.settingID == SETTINGS.INITIAL_WINDOW_SIZE:
                if self.value > MAX_WINDOW_SIZE:
                    conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FLOW_CONTROL_ERROR))
                else:
                    conn.initialWindowSize = self.value
            elif self.settingID == SETTINGS.MAX_FRAME_SIZE:
                if INITIAL_MAX_FRAME_SIZE <= self.value <= LIMIT_MAX_FRAME_SIZE:
                    conn.maxFrameSize = self.value
                else:
                    conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
            elif self.settingID == SETTINGS.MAX_HEADER_LIST_SIZE:
                conn.maxHeaderListSize = self.value
            else:
                pass
            conn.sendFrame(Settings(FLAG.ACK))


class Push_Promise(Http2Header):
    def __init__(self, flags, streamID, promisedID, padLen = 0, headers = None, table = None,  wire = ""):
        super(Push_Promise, self).__init__(TYPE.PUSH_PROMISE, flags, streamID, len(wire[9:]))
        self.promisedID = promisedID
        self.padLen = padLen
        self.headers = headers
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self, table):
        self.wire = ""
        padding = ""
        if self.flags & FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding = packHex(0, self.padLen)
        self.wire += packHex(self.promisedID, 4)
        if self.headers:
            self.wire += encode(self.headers, False, False, False, table)
        self.wire += padding

    @staticmethod
    def getFrame(flags, streamID, data, table):
        targetData = data[9:]
        index = 0
        padLen = 0
        if flags & FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", targetData[0])[0]
            padding = targetData[-padlen:]
            index += 1
        promisedID = struct.unpack(">I", targetData[index:index+4])[0] & 0x7fffffff

        headers = None
        if flags & FLAG.END_HEADERS == FLAG.END_HEADERS:
            tmp = targetData[index+4: len(targetData) if flags & FLAG.PADDED != FLAG.PADDED else -padLen]
            headers = decode(tmp, table)

        return Push_Promise(flags, streamID, promisedID, padLen, headers, None, data)

    def validate(self, conn):
        if self.streamID == 0 or con.enablePush == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        state = conn.getStreamState(self.streamID)
        if state != STATE.OPEN and state != STATE.HCLOSED_L:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        conn.addStream(self.promisedID, STATE.RESERVED_R)
        if self.Flags&FLAG.END_HEADERS != FLAG.END_HEADERS:
            #TODO buffer temporal header flagment
            pass

class Ping(Http2Header):
    def __init__(self, flags, data, streamID = 0, wire = ""):
        super(Ping, self).__init__(TYPE.PING, flags, streamID, len(wire[9:]))
        self.data = data
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = packHex(self.data, 8)

    @staticmethod
    def getFrame(flags, streamID, data):
        return Ping(flags, data[9:17], streamID, data)

    def validate(self, conn):
        if self.Length != 8:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FRAME_SIZE_ERROR))
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        if self.Flags&FLAG.ACK != FLAG.ACK:
            conn.sendFrame(Ping(FLAG.ACK, self.data))

class Goaway(Http2Header):
    def __init__(self, lastID, errorNum = ERR_CODE.NO_ERROR, debugString = "",  flags = FLAG.NO, streamID = 0, wire = ""):
        super(Goaway, self).__init__(TYPE.GOAWAY, flags, streamID, len(wire[9:]))
        self.lastID = lastID
        self.errorNum = errorNum
        self.debugString = debugString
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = packHex(self.lastID, 4)
        self.wire += packHex(self.errorNum, 4)
        self.wire += self.debugString

    @staticmethod
    def getFrame(flags, streamID, data):
        lastID, errorNum = struct.unpack(">2I", data[9:17])
        R = lastID >> 31
        lastID &= 0x7fffffff
        debugString = upackHex(data[17:])
        return Goaway(lastID, errorNum, debugString, flags, streamID, data)

    def validate(self, conn):
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE_PROTOCOL_ERROR))

class Window_Update(Http2Header):
    def __init__(self, streamID, windowSizeIncrement, flags = FLAG.NO, wire = ""):
        super(Window_Update, self).__init__(TYPE.WINDOW_UPDATE, flags, streamID, len(wire[9:]))
        self.windowSizeIncrement = windowSizeIncrement & 0x7fffffff
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = packHex(self.windowSizeIncrement, 4)

    @staticmethod
    def getFrame(flags, streamID, data):
        windowSizeIncrement = struct.unpack(">I", data[9:13])[0] & 0x7fffffff
        return Window_Update(streamID, windowSizeIncrement, flags, data)

    def validate(self, conn):
        if self.Length != 4:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FRAME_SIZE_ERROR))
        if self.windowSizeIncrement <= 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        elif self.windowSizeIncrement > (1 << 31) - 1:
            # suspicious
            if self.streamID == 0:
                conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.FLOW_CONTROL_ERROR))
            else:
                conn.sendFrame(Rst_Stream(self.streamID, ERR_CODE.FLOW_CONTROL_ERROR))
        else:
            #no cool
            conn.streams[self.StreamID].setWindowSize(windowSizeIncrement)



class Continuation(Http2Header):
    def __init__(self, flags, streamID, headerFragment, wire = ""):
        super(Continuation, self).__init__(TYPE.CONTINUATION, flags, streamID, len(wire[9:]))
        self.headerFragment = headerFragment
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = self.headerFragment

    @staticmethod
    def getFrame(flags, streamID, data):
        headerFragment = data[9:] #dangerous?
        return Continuation(flags, streamID, headerFragment, data)

    def validate(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
        if self.Flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            pass # decode and free the flagment
        else:
            pass # temporaly save to connaction
