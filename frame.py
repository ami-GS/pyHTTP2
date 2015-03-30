oimport struct
from util import *
from settings import *
from pyHPACK import HPACK
import json

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

    def string(self):
        return "Header: type=%s, flags={%s}, streamID=%d, length=%d\n" % \
            (TYPE.string(self.frame), FLAG.string(self.flags), self.streamID, self.length)

class Data(Http2Header):
    def __init__(self, data, streamID, **kwargs):
        self.padLen = kwargs.get("padLen", 0)
        self.data = data
        flags = kwargs.get("flags", FLAG.NO)
        wire = kwargs.get("wire", "")
        if self.padLen:
            flags |= FLAG.PADDING
        super(Data, self).__init__(TYPE.DATA, flags, streamID, len(wire[9:]))
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
        return Data(content, streamID, flags=flags, padLen=padLen, wire=data)

    def validate(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        state = conn.getStreamState(self.streamID)
        if state == STATE.CLOSED:
            conn.sendFrame(Rst_Stream(self.streamID, err=ERR_CODE.PROTOCOL_ERROR))
        if state != STATE.OPEN and state != STATE.HCLOSED_L:
            conn.sendFrame(Rst_Stream(self.streamID, err=ERR_CODE.STREAM_CLOSED))
        if self.flags&FLAG.PADDED == FLAG.PADDED and self.padLen > (len(self.wire)-1):
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))

    def string(self):
        return "%s\tdata=%s, padding length=%s\n" % \
            (super(Data, self).string(), self.data, self.padLen)

class Headers(Http2Header):
    def __init__(self, headers, streamID, **kwargs):
        self.padLen = kwargs.get("padLen", 0)
        self.E = kwargs.get("E", 0)
        self.streamDependency = kwargs.get("streamDependency", 0)
        self.weight = kwargs.get("weight", 0)
        flags = kwargs.get("flags", FLAG.NO)
        wire  = kwargs.get("wire", "")
        if self.padLen:
            flags |= FLAG.PADDING
        if self.streamDependency:
            flags |= FLAG.PRIORITY
        super(Headers, self).__init__(TYPE.HEADERS, flags, streamID, len(wire[9:]))
        self.headers = headers
        if wire:
            self.headerFlagment = kwargs.get("flagment", "")
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self.headerFlagment = HPACK.encode(self.headers, False, False, False, kwargs.get("table"))
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        padding = ""
        if self.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        if self.flags&FLAG.PRIORITY == FLAG.PRIORITY:
            if self.E:
                self.wire += packHex(self.streamDependency | 0x80000000, 4)
            else:
                self.wire += packHex(self.streamDependency, 4)
            self.wire += packHex(self.weight, 1)
        self.wire += self.headerFlagment + padding

    @staticmethod
    def getFrame(flags, streamID, data):
        targetData = data[9:]
        index = 0
        padLen = 0
        E = 0
        streamDependency = 0
        weight = 0
        if flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct,unpack(">B", targetData[0])[0]
            padding = targetData[-padLen:]
            index += 1
        if flags&FLAG.PRIORITY == FLAG.PRIORITY:
            streamDependency, weight = struct.unpack(">IB", targetData[index:index+5])
            E = streamDependenct >> 31
            streamDependency &= 0x7fffffff
            index += 5
        if padLen:
            headerFlagment = targetData[index:-padLen]
        else:
            headerFlagment = targetData[index:]

        return Headers([], streamID, flags=flags, flagment=headerFlagment, padLen=padLen,
                       E=E, straemDependency=streamDependency, weight=weight, wire=data)

    def validate(self, conn):
        state = conn.getStreamState(self.streamID)
        if state == STATE.RESERVED_R:
            conn.setStreamState(self.streamID, STATE.HCLOSED_L)
        else:
            conn.setStreamState(self.streamID, STATE.OPEN)
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            conn.sendFrame(Data("return Data!", self.streamID, flags=FLAG.END_STREAM))
        else:
            conn.appendFlagment(self.streamID, self.headerFlagment)
        if self.flags&FLAG.END_STREAM == FLAG.END_STREAM:
            conn.setStreamState(self.streamID, STATE.HCLOSED_R)

    def string(self):
        return "%s\theaders=%s, padding length=%s, E=%d, stream dependency=%d" % \
            (super(Headers, self).string(), "".join("".join(json.dumps(self.headers).split("\'")).split("\"")), self.padLen, self.E, self.streamDependency)


class Priority(Http2Header):
    def __init__(self, streamID, E, streamDependency, weight, **kwargs):
        flags = kwargs.get("flags", FLAG.NO)
        wire = kwargs.get("wire", "")
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
        return Priority(streamID, E, streamDependency, weight, flags=flags, wire=data)

    def validate(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.length != 5:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))

    def string(self):
        return "%s\tE=%d, stream dependency=%d, weight=%d\n" % \
            (super(Priority, self).string(), self.E, self.streamDependency, self.weight)


class Rst_Stream(Http2Header):
    def __init__(self, streamID, **kwargs):
        flags = kwargs.get("flags", FLAG.NO)
        self.err = kwargs.get("err", ERR_CODE.NO_ERROR)
        wire = kwargs.get("wire", "")
        super(Rst_Stream, self).__init__(TYPE.RST_STREAM, flags, streamID, len(wire[9:]))
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = packHex(self.err, 4)

    @staticmethod
    def getFrame(flags, streamID, data):
        err = struct.unpack(">I", data[9:])[0]
        return Rst_Stream(streamID, err=err, flags=flags, wire=data)

    def validate(self, conn):
        if self.length != 4:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.streamID == 0 or conn.getStreamState(self.streamID) == STATE.IDLE:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        else:
            conn.setStreamState(self.streamID, STATE.CLOSED)

    def string(self):
        return "%s\terror=%s" % (super(Rst_Stream, self).string(), ERR_CODE.string(self.errorNum))


class Settings(Http2Header):
    def __init__(self, settingID=SETTINGS.NO, value=0, **kwargs):
        streamID = kwargs.get("streamID", 0)
        flags = kwargs.get("flags", FLAG.NO)
        wire = kwargs.get("wire", "")
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
        return Settings(settingID, value, flags=flags, streamID=streamID, wire=data)

    def validate(self, conn):
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.length % 6 != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.flags&FLAG.ACK == FLAG.ACK:
            if self.length != 0:
                conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        elif self.length:
            if self.settingID == SETTINGS.HEADER_TABLE_SIZE:
                conn.setHeaderTableSize(self.value)
            elif self.settingID == SETTINGS.ENABLE_PUSH:
                if self.value == 1 or value == 0:
                    conn.enablePush = value
                else:
                    conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
            elif self.settingID == SETTINGS.MAX_CONCURRENT_STREAMS:
                if self.value <= 100:
                    print("Warnnig: max_concurrent_stream below 100 is not recomended")
                conn.maxConcurrentStreams = self.value
            elif self.settingID == SETTINGS.INITIAL_WINDOW_SIZE:
                if self.value > MAX_WINDOW_SIZE:
                    conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FLOW_CONTROL_ERROR))
                else:
                    conn.initialWindowSize = self.value
            elif self.settingID == SETTINGS.MAX_FRAME_SIZE:
                if INITIAL_MAX_FRAME_SIZE <= self.value <= LIMIT_MAX_FRAME_SIZE:
                    conn.maxFrameSize = self.value
                else:
                    conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
            elif self.settingID == SETTINGS.MAX_HEADER_LIST_SIZE:
                conn.maxHeaderListSize = self.value
            else:
                pass
            conn.sendFrame(Settings(flags=FLAG.ACK))

    def string(self):
        return "%s\tsetting=%s, value=%d" % \
            (super(Settings, self).string(), SETTINGS.string(self.settingID), self.value)


class Push_Promise(Http2Header):
    def __init__(self, headers, streamID, promisedID, **kwargs):
        flags = kwargs.get("flags", FLAG.NO)
        self.padLen = kwargs.get("padLen", 0)
        wire = kwargs.get("wire", "")
        if self.padLen:
            flags |= FLAG.PADDING
        super(Push_Promise, self).__init__(TYPE.PUSH_PROMISE, flags, streamID, len(wire[9:]))
        self.promisedID = promisedID
        self.headers = headers
        if wire:
            self.headerFlagment = kwargs.get("flagment", "")
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self.headerFlagment = HPACK.encode(self.headers, False, False, False, kwargs.get("table"))
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = ""
        padding = ""
        if self.flags & FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding = packHex(0, self.padLen)
        self.wire += packHex(self.promisedID, 4)
        self.wire += self.headerFlagment + padding

    @staticmethod
    def getFrame(flags, streamID, data):
        targetData = data[9:]
        index = 0
        padLen = 0
        if flags & FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", targetData[0])[0]
            padding = targetData[-padlen:]
            index += 1
        promisedID = struct.unpack(">I", targetData[index:index+4])[0] & 0x7fffffff
        headerFlagment = targetData[index+4: len(targetData) if flags & FLAG.PADDED != FLAG.PADDED else -padLen]

        return Push_Promise([], streamID, promisedID, flags=flags, 
                            flagment=headerFlagment, padLen=padLen, wire=data)

    def validate(self, conn):
        if self.streamID == 0 or conn.enablePush == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        state = conn.getStreamState(self.streamID)
        if state != STATE.OPEN and state != STATE.HCLOSED_L:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        conn.addStream(self.promisedID, STATE.RESERVED_R)
        if self.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            #send data
            conn.initFlagment(self.streamID)
        else:
            conn.appendFlagment(self.streamID, self.headerFlagment)

    def string(self):
        return "%s\tpromisedID=%d, padding length=%d, headers=%s" % (super(Push_Promise, self).string(), self.promisedID, self.padLen,  "".join("".join(json.dumps(self.headers).split("\'")).split("\"")))


class Ping(Http2Header):
    def __init__(self, data = "", **kwargs):
        wire = kwargs.get("wire", "")
        flags = kwargs.get("flags", FLAG.NO)
        sID = kwargs.get("streamID", 0)
        self.data = data
        super(Ping, self).__init__(TYPE.PING, flags, sID, len(wire[9:]))
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
        return Ping(flags = flags, data = data[9:17], streamID = streamID, wire = data)

    def validate(self, conn):
        if self.length != 8:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.flags&FLAG.ACK != FLAG.ACK:
            conn.sendFrame(Ping(self.data, flags = FLAG.ACK))

    def string(self):
        return "%s\tdata=%s" % (super(Ping, self).string(), self.data)

class Goaway(Http2Header):
    def __init__(self, lastID, **kwargs):
        flags = kwargs.get("flags", FLAG.NO)
        streamID = kwargs.get("streamID", 0)
        wire = kwargs.get("wire", "")
        super(Goaway, self).__init__(TYPE.GOAWAY, flags, streamID, len(wire[9:]))
        self.lastID = lastID
        self.err = kwargs.get("err", ERR_CODE.NO_ERROR)
        print kwargs
        self.debugString = kwargs.get("debugString", "")
        if wire:
            self.wire = wire[9:]
            self.headerWire = wire[:9]
        else:
            self._makeWire()
            self._makeHeaderWire()

    def _makeWire(self):
        self.wire = packHex(self.lastID, 4)
        self.wire += packHex(self.err, 4)
        self.wire += self.debugString

    @staticmethod
    def getFrame(flags, streamID, data):
        lastID, err = struct.unpack(">2I", data[9:17])
        R = lastID >> 31
        lastID &= 0x7fffffff
        debugString = data[17:]
        return Goaway(lastID, err=err, debugString=debugString, flags=flags, streamID=streamID, wire=data)

    def validate(self, conn):
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE_PROTOCOL_ERROR))

    def string(self):
        return "%s\tlast streamID=%d, error=%s, debug string=%s" % (super(Goaway, self).string(), self.lastID, ERR_CODE.string(self.err), self.debugString)


class Window_Update(Http2Header):
    def __init__(self, streamID, windowSizeIncrement, **kwargs):
        flags = kwargs.get("flags", FLAG.NO)
        wire = kwargs,get("wire", "")
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
        return Window_Update(streamID, windowSizeIncrement, flags=flags, wire=data)

    def validate(self, conn):
        if self.length != 4:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.windowSizeIncrement <= 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        elif self.windowSizeIncrement > (1 << 31) - 1:
            # suspicious
            if self.streamID == 0:
                conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FLOW_CONTROL_ERROR))
            else:
                conn.sendFrame(Rst_Stream(self.streamID, err=ERR_CODE.FLOW_CONTROL_ERROR))
        else:
            #no cool
            conn.streams[self.streamID].setWindowSize(self.windowSizeIncrement)

    def string(self):
        return "%s\twindow size increment=%s" % (super(Window_Update, self).string(), self.windowSizeIncrement)


class Continuation(Http2Header):
    #def __init__(self, flags, streamID, fragment, wire = ""):
    def __init__(self, streamID, **kwargs):
        flags = kwargs.get("flags", FLAG.NO)
        wire = kwargs.get("wire", "")
        super(Continuation, self).__init__(TYPE.CONTINUATION, flags, streamID, len(wire[9:]))
        self.headerFragment = kwargs.get("fragment", "")
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
        return Continuation(streamID, flags=flags, fragment=headerFragment, wire=data)

    def validate(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            #send data
            conn.initFlagment(self.streamID)
        else:
            conn.appendFlagment(self.streamID, self.headerFlagment)

    def string(self):
        return "%s" % (super(Continuation, self).string())
