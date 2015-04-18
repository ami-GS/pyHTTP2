import struct
from util import *
from settings import *
import json
from pyHPACK import HPACK

def getFrameFunc(frame_type):
    if frame_type == TYPE.DATA:
        return Data.getFrame
    elif frame_type == TYPE.HEADERS:
        return Headers.getFrame
    elif frame_type == TYPE.PRIORITY:
        return Priority.getFrame
    elif frame_type == TYPE.RST_STREAM:
        return Rst_Stream.getFrame
    elif frame_type == TYPE.SETTINGS:
        return Settings.getFrame
    elif frame_type == TYPE.PUSH_PROMISE:
        return Push_Promise.getFrame
    elif frame_type == TYPE.PING:
        return Ping.getFrame
    elif frame_type == TYPE.GOAWAY:
        return Goaway.getFrame
    elif frame_type == TYPE.WINDOW_UPDATE:
        return Window_Update.getFrame
    elif frame_type == TYPE.CONTINUATION:
        return Continuation.getFrame
    else:
        print "WARNNING: undefined frame type"
        return #raise

class Http2Header(object):
    def __init__(self, frame=None, flags=None, streamID=0, length=0, info=None, **kwargs):
        if info:
            self.type = info.type
            self.flags = info.flags
            self.streamID = info.streamID
            self.length = info.length
        else:
            self.type = frame
            self.flags = flags
            self.streamID = streamID
            self.length = length
        self.headerWire = kwargs.get("headerWire", "")

    def _makeHeaderWire(self):
        self.length = len(self.wire)
        self.headerWire = struct.pack(">I2BI", self.length, self.type, self.flags, self.streamID)[1:]

    def setLength(self, length):
        self.length = length

    def getWire(self):
        return self.headerWire + self.wire

    @staticmethod
    def getHeaderInfo(data):
        length, frame, flags, streamID = struct.unpack(">I2BI", "\x00"+data)
        return Http2Header(frame, flags, streamID, length, headerWire=data)

    def string(self):
        return "Header: type=%s, flags={%s}, streamID=%d, length=%d\n" % \
            (frameC.apply(TYPE.string(self.type)), FLAG.string(self.flags), self.streamID, self.length)

class Data(Http2Header):
    def __init__(self, data, streamID, **kwargs):
        self.padLen = kwargs.get("padLen", 0)
        self.data = data
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", "")
        if info:
            super(Data, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            if self.padLen:
                flags |= FLAG.PADDING
            super(Data, self).__init__(TYPE.DATA, flags, streamID, len(self.wire))

    def makeWire(self):
        padding = ""
        if self.flags&FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding += packHex(0, self.padLen)
        self.wire += self.data + padding
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        index = 0
        padLen = 0
        if info.flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            index += 1
        content = data[index: -padLen if padLen else len(data)]
        return Data(content, info.streamID, info=info, padLen=padLen, wire=data)

    def recvEval(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        state = conn.getStreamState(self.streamID)
        if state == STATE.CLOSED:
            conn.sendFrame(Rst_Stream(self.streamID, err=ERR_CODE.PROTOCOL_ERROR))
        if state != STATE.OPEN and state != STATE.HCLOSED_L:
            conn.sendFrame(Rst_Stream(self.streamID, err=ERR_CODE.STREAM_CLOSED))
        if self.flags&FLAG.PADDED == FLAG.PADDED and self.padLen > (len(self.wire)-1):
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        conn.useWindow(self.streamID, len(self.data)*8)

    def sendEval(self, conn):
        conn.useWindow(self.streamID, len(self.data)*8)

    def string(self):
        return "%s\tdata=%s, padding length=%s\n" % \
            (super(Data, self).string(), self.data, self.padLen)

class Headers(Http2Header):
    def __init__(self, headers, streamID, **kwargs):
        self.headers = headers
        self.padLen = kwargs.get("padLen", 0)
        self.E = kwargs.get("E", 0)
        self.streamDependency = kwargs.get("streamDependency", 0)
        self.weight = kwargs.get("weight", 0)
        self.headerFlagment = kwargs.get("flagment", "")
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Headers, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            if self.padLen:
                flags |= FLAG.PADDING
            if self.streamDependency:
                flags |= FLAG.PRIORITY
            super(Headers, self).__init__(TYPE.HEADERS, flags, streamID, len(self.wire))

    def makeWire(self):
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
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        index = 0
        padLen = 0
        E = 0
        streamDependency = 0
        weight = 0
        if info.flags&FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            padding = data[-padLen:]
            index += 1
        if info.flags&FLAG.PRIORITY == FLAG.PRIORITY:
            streamDependency, weight = struct.unpack(">IB", data[index:index+5])
            E = streamDependency >> 31
            streamDependency &= 0x7fffffff
            index += 5
        headerFlagment = data[index: -padLen if padLen else len(data)]

        return Headers([], info.streamID, info=info, flagment=headerFlagment, padLen=padLen,
                       E=E, streamDependency=streamDependency, weight=weight, wire=data)

    def recvEval(self, conn):
        state = conn.getStreamState(self.streamID)
        if state == STATE.RESERVED_R:
            conn.setStreamState(self.streamID, STATE.HCLOSED_L)
        else:
            conn.setStreamState(self.streamID, STATE.OPEN)
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            with open(DOCUMENT_ROOT+"index.html") as f:
                conn.sendFrame(Data("".join(f.readlines()), self.streamID, flags=FLAG.END_STREAM))
        else:
            conn.appendFlagment(self.streamID, self.headerFlagment)
        if self.flags&FLAG.END_STREAM == FLAG.END_STREAM:
            conn.setStreamState(self.streamID, STATE.HCLOSED_R)
        conn.lastStreamID = self.streamID

    def sendEval(self, conn):
        self.headerFlagment = HPACK.encode(self.headers, False, False, False, conn.table)
        state = conn.getStreamState(self.streamID)
        #TODO:this should be implemented in connection
        if self.flags&FLAG.PRIORITY == FLAG.PRIORITY:
            conn.streams[self.streamID].weight = self.weight
            conn.streams[self.streamID].setParentStream(self.E, conn.streams[self.streamDependency])
        if state == STATE.IDLE:
            conn.setStreamState(self.streamID, STATE.OPEN)
        elif state == STATE.RESERVED_L:
            conn.setStreamState(self.streamID, STATE.HCLOSED_R)

    def string(self):
        return "%s\theaders=%s, padding length=%s, E=%d, stream dependency=%d" % \
            (super(Headers, self).string(), "".join("".join(json.dumps(self.headers).split("\'")).split("\"")), self.padLen, self.E, self.streamDependency)


class Priority(Http2Header):
    def __init__(self, streamID, E, streamDependency, weight, **kwargs):
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Priority, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            super(Priority, self).__init__(TYPE.PRIORITY, flags, streamID, len(self.wire))
            self.E = E
            self.streamDependency = streamDependency
            self.weight = self.weight

    def makeWire(self):
        if self.E:
            self.wire = packHex(self.streamDependency | 0x80000000, 4)
        else:
            self.wire = packHex(self.streamDependency, 4)
        self.wire += packHex(self.weight, 1)
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        streamDependency, weight = struct.unpack(">IB", data[:5])
        E = streamDependency >> 31
        streamDependency &= 0x7fffffff
        return Priority(info.streamID, E, streamDependency, weight, info=info, wire=data)

    def recvEval(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.length != 5:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))

    def sendEval(self, conn):
        pass

    def string(self):
        return "%s\tE=%d, stream dependency=%d, weight=%d\n" % \
            (super(Priority, self).string(), self.E, self.streamDependency, self.weight)


class Rst_Stream(Http2Header):
    def __init__(self, streamID, **kwargs):
        self.wire = kwargs.get("wire", "")
        self.err = kwargs.get("err", ERR_CODE.NO_ERROR)
        info = kwargs.get("info", None)
        if info:
            super(Rst_Stream, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            super(Rst_Stream, self).__init__(TYPE.RST_STREAM, flags, streamID, len(self.wire))

    def makeWire(self):
        self.wire = packHex(self.err, 4)
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        err = struct.unpack(">I", data)[0]
        return Rst_Stream(info.streamID, err=err, info=info, wire=data)

    def recvEval(self, conn):
        if self.length != 4:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.streamID == 0 or conn.getStreamState(self.streamID) == STATE.IDLE:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        else:
            conn.setStreamState(self.streamID, STATE.CLOSED)

    def sendEval(self, conn):
        conn.setStreamState(self.streamID, STATE.CLOSED)

    def string(self):
        return "%s\terror=%s" % (super(Rst_Stream, self).string(), ERR_CODE.string(self.err))


class Settings(Http2Header):
    def __init__(self, settingID=SETTINGS.NO, value=0, **kwargs):
        self.settingID = settingID
        self.value = value
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Settings, self).__init__(info=info)
        else:
            streamID = kwargs.get("streamID", 0)
            flags = kwargs.get("flags", FLAG.NO)
            super(Settings, self).__init__(TYPE.SETTINGS, flags, streamID, len(self.wire))

    def makeWire(self):
        if self.flags & FLAG.ACK == FLAG.ACK:
            return
        self.wire = packHex(self.settingID, 2) + packHex(self.value, 4)
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        settingID, value = struct.unpack(">HI", data)
        return Settings(settingID, value, info=info, wire=data)

    def recvEval(self, conn):
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.length % 6 != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.flags&FLAG.ACK == FLAG.ACK:
            if self.length != 0:
                conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
                return
            conn.peerSettingACK = True
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
                    conn.setInitialWindowSize(self.value)
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

    def sendEval(self, conn):
        conn.peerSettingACK = False

    def string(self):
        return "%s\tsetting=%s, value=%d" % \
            (super(Settings, self).string(), SETTINGS.string(self.settingID), self.value)


class Push_Promise(Http2Header):
    def __init__(self, headers, streamID, promisedID, **kwargs):
        self.promisedID = promisedID
        self.headers = headers
        self.padLen = kwargs.get("padLen", 0)
        self.headerFlagment = kwargs.get("flagment", "")
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Push_Promise, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            if self.padLen:
                flags |= FLAG.PADDING
            super(Push_Promise, self).__init__(TYPE.PUSH_PROMISE, flags, streamID, len(self.wire))

    def makeWire(self):
        self.wire = ""
        padding = ""
        if self.flags & FLAG.PADDED == FLAG.PADDED:
            self.wire += packHex(self.padLen, 1)
            padding = packHex(0, self.padLen)
        self.wire += packHex(self.promisedID, 4)
        self.wire += self.headerFlagment + padding
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        index = 0
        padLen = 0
        if info.flags & FLAG.PADDED == FLAG.PADDED:
            padLen = struct.unpack(">B", data[0])[0]
            index += 1
        promisedID = struct.unpack(">I", data[index:index+4])[0] & 0x7fffffff
        headerFlagment = data[index+4: -padLen if padLen else len(data)]

        return Push_Promise([], info.streamID, promisedID, info=info, 
                            flagment=headerFlagment, padLen=padLen, wire=data)

    def recvEval(self, conn):
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

    def sendEval(self, conn):
        self.headerFlagment = HPACK.encode(self.headers, False, False, False, conn.table)
        if conn.getStreamState(self.streamID) == STATE.IDLE:
            conn.setStreamState(self.streamID, STATE.RESERVED_L)

    def string(self):
        return "%s\tpromisedID=%d, padding length=%d, headers=%s" % (super(Push_Promise, self).string(), self.promisedID, self.padLen,  "".join("".join(json.dumps(self.headers).split("\'")).split("\"")))


class Ping(Http2Header):
    def __init__(self, data = "", **kwargs):
        self.wire = kwargs.get("wire", "")
        self.data = data
        info = kwargs.get("info", None)
        if info:
            super(Ping, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            sID = kwargs.get("streamID", 0)
            super(Ping, self).__init__(TYPE.PING, flags, sID, len(self.wire))

    def makeWire(self):
        self.wire = packHex(self.data, 8)
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        return Ping(data = data, info=info, wire = data)

    def recvEval(self, conn):
        if self.length != 8:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.FRAME_SIZE_ERROR))
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.flags&FLAG.ACK != FLAG.ACK:
            conn.sendFrame(Ping(self.data, flags = FLAG.ACK))

    def sendEval(self, conn):
        pass

    def string(self):
        return "%s\tdata=%s" % (super(Ping, self).string(), self.data)

class Goaway(Http2Header):
    def __init__(self, lastID, **kwargs):
        self.lastID = lastID
        self.err = kwargs.get("err", ERR_CODE.NO_ERROR)
        self.debugString = kwargs.get("debugString", "")
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Goaway, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            streamID = kwargs.get("streamID", 0)
            super(Goaway, self).__init__(TYPE.GOAWAY, flags, streamID, len(self.wire))

    def makeWire(self):
        self.wire = packHex(self.lastID, 4)
        self.wire += packHex(self.err, 4)
        self.wire += self.debugString
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        lastID, err = struct.unpack(">2I", data[:8])
        R = lastID >> 31
        lastID &= 0x7fffffff
        debugString = data[8:]
        return Goaway(lastID, err=err, debugString=debugString, info=info, wire=data)

    def recvEval(self, conn):
        if self.streamID != 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE_PROTOCOL_ERROR))
        #here?
        conn.sock.close()

    def sendEval(self, conn):
        conn.is_goaway = True

    def string(self):
        return "%s\tlast streamID=%d, error=%s, debug string=%s" % (super(Goaway, self).string(), self.lastID, ERR_CODE.string(self.err), self.debugString)


class Window_Update(Http2Header):
    def __init__(self, streamID, windowSizeIncrement, **kwargs):
        self.windowSizeIncrement = windowSizeIncrement & 0x7fffffff
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Window_Update, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            super(Window_Update, self).__init__(TYPE.WINDOW_UPDATE, flags, streamID, len(self.wire))

    def makeWire(self):
        self.wire = packHex(self.windowSizeIncrement, 4)
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        windowSizeIncrement = struct.unpack(">I", data)[0] & 0x7fffffff
        return Window_Update(info.streamID, windowSizeIncrement, info=info, wire=data)

    def recvEval(self, conn):
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
            conn.recoverWindow(self.streamID, self.windowSizeIncrement)

    def sendEval(self, conn):
        conn.recoverWindow(self.streamID, self.windowSizeIncrement)

    def string(self):
        return "%s\twindow size increment=%s" % (super(Window_Update, self).string(), self.windowSizeIncrement)


class Continuation(Http2Header):
    def __init__(self, streamID, **kwargs):
        self.headerFragment = kwargs.get("fragment", "")
        self.wire = kwargs.get("wire", "")
        info = kwargs.get("info", None)
        if info:
            super(Continuation, self).__init__(info=info)
        else:
            flags = kwargs.get("flags", FLAG.NO)
            super(Continuation, self).__init__(TYPE.CONTINUATION, flags, streamID, len(self.wire))

    def makeWire(self):
        self.wire = self.headerFragment
        self._makeHeaderWire()

    @staticmethod
    def getFrame(info, data):
        headerFragment = data #dangerous?
        return Continuation(info.streamID, info=info, fragment=headerFragment, wire=data)

    def recvEval(self, conn):
        if self.streamID == 0:
            conn.sendFrame(Goaway(conn.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
        if self.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            #send data
            conn.initFlagment(self.streamID)
        else:
            conn.appendFlagment(self.streamID, self.headerFlagment)

    def sendEval(self, conn):
        pass

    def string(self):
        return "%s" % (super(Continuation, self).string())
