from pyHPACK.HPACK import encode, decode
from settings import *
import socket
from binascii import hexlify

FLAG = BaseFlag
TYPE = FrameType
SET = Settings
ERR = ErrorCode

wireWrapper = lambda x: "".join([chr(int(x[i:i+2], 16)) for i in range(0, len(x), 2)])

def packHex(val, l):
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

class HTTP2Base(object):
    def __init__(self, host, port, table = None):
        self.table = table
        self.host, self.port = host, port
        self.padLen = 0
        self.lastStream_id = None
        self.streams = {0:"open"} #streams should be shared with both peer?
        self.enablePush = 1
        self.maxConcurrentStreams = -1
        self.initialWindowSize = (1 << 16) -1
        self.maxFrameSize = 1 << 14 # octet
        self.maxHeaderListSize = -1
        self.goAwayStream_id = -1
        self.readyToPayload = False
        self.con = None

    def send(self, frame):
        self.sock.send(frame)

    def resp(self, frame):
        self.con.send(frame)

    def parseData(self, data):
        def _parseFrameHeader(data):
            return int(hexlify(data[:3]), 16), data[3:4], \
                data[4:5], int(hexlify(data[5:9]),16)

        def _data(data, Flag, stream_id):
            if stream_id == 0:
                print("err:PROTOCOL_ERROR")
            if self.streams[stream_id] == "closed":
                print("err:STREAM_CLOSED")
            padLen = 0
            if Flag == FLAG.PADDED:
                padLen = int(hexlify(data[0]), 16)
            content = data[1: len(data) if Flag != FLAG.PADDED else -padLen]
            print("DATA:%s" % (content))

        def _headers(data, Flag):
            index = 0
            if Flag == FLAG.PADDED:
                padLen = int(hexlify(data[0]), 16)
                padding = data[-padLen:]
                index = 1
            elif Flag == FLAG.PRIORITY:
                E = int(hexlify(data[:4]), 16) & 0x80
                streamDepend = int(hexlify(data[:4]), 16) & 0x7fffffff
                weight = int(hexlify(data[5]), 16)
                index = 5
            Wire = data[index: len(data) if Flag != FLAG.PADDED else -padLen]

            #tempral test
            self.resp(self.makeFrame(TYPE.DATA, FLAG.NO, 1, data = "aiueoDATA!!!", padLen = 0))

            print(decode(hexlify(Wire), self.table))

        def _priority():
            pass
        def _rst_stream():
            pass
        def _settings(data, Length, Flag, Stream_id):
            if Stream_id != 0:
                print("err:PROTOCOL_ERROR")
            if Flag == FLAG.ACK:
                if Length != 0:
                    print("err:FRAME_SIZE_ERROR")
            elif len(data):
                Identifier = int(hexlify(data[:2]), 16)
                Value = int(hexlify(data[2:6]), 16)
                if Identifier == SET.HEADER_TABLE_SIZE:
                    self.table.setMaxHeaderTableSize(Value)
                elif Identifier == SET.ENABLE_PUSH:
                    if Value == 1 or Value == 0:
                        self.enablePush = Value
                    else:
                        print("err")
                elif Identifier == SET.MAX_CONCURRENT_STREAMS:
                    if Value < 100:
                        print("Warnnig: max_concurrent_stream below 100 is not recomended")
                    self.maxConcurrentStreams = Value
                elif Identifier == SET.INITIAL_WINDOW_SIZE:
                    if Value > MAX_WINDOW_SIZE:
                        print("err:FLOW_CONTROL_ERROR")
                    else:
                        self.initialWindowSize = Value
                elif Identifier == SET.MAX_FRAME_SIZE:
                    if INITIAL_MAX_FRAME_SIZE <= Value  <= LIMIT_MAX_FRAME_SIZE:
                        self.maxFrameSize = Value
                    else:
                        print("err:PROTOCOL_ERROR")
                elif Identifier == SET.MAX_HEADER_LIST_SIZE:
                    self.maxHeaderListSize = Value # ??
                else:
                    pass # must ignore
                # must send ack
                self.resp(self.makeFrame(TYPE.SETTINGS, FLAG.ACK, 0, ident=SET.NO, value = ""))

        def _ping(data, Length, Flag, Stream_id):
            if Length != 8:
                print("err:FRAME_SIZE_ERROR")
            if Stream_id != 0:
                print("err:PROTOCOL_ERROR")
            if Flag != FLAG.ACK:
                # must send ping with flag == ack
                print("ping response !")
                self.resp(self.makeFrame(TYPE.PING, FLAG.ACK, 0, ping = data[:8]))
            else:
                print("PING:%s" % (data[:8]))
                
        def _goAway(data, Length, Stream_id):
            if Stream_id != 0:
                print("err:PROTOCOL_ERROR")
            R = int(hexlify(data[0]), 16) & 0x80
            lastStreamID = int(hexlify(data[:4]), 16) & 0x7fffffff
            errCode = int(hexlify(data[4:8]), 16)
            if Length > 8:
                additionalData =  int(hexlify(data[64:]), 16)
            self.goAwayStream_id = lastStreamID

        def _window_update():
            pass
        def _continuation():
            pass

        Length, Type, Flags, Stream_id = 0, '\x00', '\x00', 0 #here?
        while len(data) or Type == TYPE.SETTINGS:
            if data.startswith(CONNECTION_PREFACE):
                #send settings (this may be empty)
                data = data.lstrip(CONNECTION_PREFACE)
            else:
                print(Length, hexlify(Type), hexlify(Flags), Stream_id, self.readyToPayload)
                if self.readyToPayload:
                    if Type == TYPE.DATA:
                        _data(data[:Length], Flags, Stream_id)
                    elif Type == TYPE.HEADERS:
                        _headers(data[:Length], Flags)
                    elif Type == TYPE.PRIORITY:
                        _priority(data[:Length])
                    elif Type == TYPE.RST_STREAM:
                        _rst_stream(data[:Length])
                    elif Type == TYPE.SETTINGS:
                        _settings(data, Length, Flags, Stream_id)
                    elif Type == TYPE.PING:
                        _ping(data[:Length], Length, Flags, Stream_id)
                    elif Type == TYPE.GOAWAY:
                        _goAway(data[:Length], Length, Stream_id)
                    elif Type == TYPE.WINDOW_UPDATE:
                        _window_update(data[:Length])
                    elif Type == TYPE.CONTINUATION:
                        _continuation(data[:Length])
                    else:
                        print("err:undefined frame type",Type)
                    data = data[Length:]
                    Length, Type, Flags, Stream_id = 0, '\x00', '\x00', 0 #here?
                    self.readyToPayload = False
                else:
                    Length, Type, Flags, Stream_id = _parseFrameHeader(data)
                    print(hexlify(data))
                    print(Length, hexlify(Type), hexlify(Flags), Stream_id, "set")
                    data = data[FRAME_HEADER_SIZE:]
                    self.readyToPayload = True

    def makeFrame(self, Type, flag=FLAG.NO, stream_id=0, **kwargs):
        def _HTTP2Frame(length, Type, flag, stream_id):
            return packHex(length, 3) + packHex(Type, 1) + packHex(flag, 1) + packHex(stream_id, 4)

        def _data(flag, stream_id, data, padLen = 0):
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(padLen, 1)
                padding += packHex(0, padLen)
            frame += data #TODO data length should be configured
            return frame + padding

        def _headers(flag):
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(self.padLen, 1) # Pad Length
                padding = packHex(0, self.padLen)
            elif flag == FLAG.PRIORITY:
                # 'E' also should be here
                frame += packHex(0, 4) # Stream Dependency
                frame += packHex(0, 1) # Weight
            wire = wireWrapper(encode(self.headers, True, True, True, self.table))
            # continuation frame should be used if length is ~~ ?
            frame += wire + padding
            return frame

        def _priority():
            return ""

        def _rst_stream():
            return ""

        def _settings(flag, identifier = SET.NO, value = 0):
            if flag == FLAG.NO or flag == FLAG.ACK:
                return ""
            frame = packHex(identifier, 2) + packHex(value, 4)
            return frame

        def _push_promise():
            return ""

        def _ping(value):
            return packHex(value, 8)

        def _goAway(err, debug):
            # R also should be here
            frame = packHex(self.lastStream_id, 4)
            frame += packHex(err, 4)
            frame += debug if debug else ""
            return frame

        def _window_update():
            return ""

        def _continuation(wire):
            # TODO wire length and fin flag should be specified
            return wire

        if Type == TYPE.DATA:
            frame = _data(flag, 1, kwargs["data"], kwargs["padLen"]) # TODO  manage stream_id
        elif Type == TYPE.HEADERS:
            frame = _headers(flag)
        elif Type == TYPE.PRIORITY:
            frame = _priority()
        elif Type == TYPE.RST_STREAM:
            frame = _rst_stream()
        elif Type == TYPE.SETTINGS:
            frame = _settings(flag, kwargs["ident"], kwargs["value"])
        elif Type == TYPE.PING:
            frame = _ping(kwargs["ping"])
        elif Type == TYPE.GOAWAY:
            frame = _goAway(kwargs["err"], kwargs["debug"])
        elif Type == TYPE.WINDOW_UPDATE:
            frame = _window_update()
        elif Type == TYPE.CONTINUATION:
            frame = _continuation()
        else:
            print("err:undefined frame type", Type)
        http2Frame = _HTTP2Frame(len(frame), Type, flag, stream_id)
        return http2Frame + frame

    def addStream(self):
        self.lastStream_id += 2
        self.streams[self.lastStream_id] = "open" #closed?

    def setTable(self, table):
        self.table = table

    def setHeaders(self, headers):
        self.headers = headers

class Server(HTTP2Base):
    def __init__(self, host, port, table = None):    
        super(Server, self).__init__(host, port, table)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lastStream_id = 2
        self.streams[self.lastStream_id] = "open"

    def runServer(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(1) # number ?
        import time
        while True:
            print("Connection waiting...")
            self.con, addr = self.sock.accept()
            data = "dummy"
            while len(data):
                data = self.con.recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8) # here should use window length ?
                self.parseData(data)

class Client(HTTP2Base):
    def __init__(self, host, port, table = None):
        super(Client, self).__init__(host, port, table)
        self.lastStream_id = 1
        self.streams[self.lastStream_id] = "open"
        self.sock = socket.create_connection((host, port), 5)
