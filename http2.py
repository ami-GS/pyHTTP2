from pyHPACK.HPACK import encode, decode
from settings import *
import socket
from binascii import hexlify, unhexlify

FLAG = BaseFlag
TYPE = FrameType
SET = Settings
ERR = ErrorCode

def packHex(val, l):
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

def upackHex(val):
    return int(hexlify(val), 16)

class HTTP2Base(object):
    def __init__(self, host, port, table = None):
        self.table = table
        self.host, self.port = host, port
        self.lastStream_id = None
        self.streams = {0:"open"} #streams should be shared with both peer?
        self.enablePush = SET.INIT_VALUE[2]
        self.maxConcurrentStreams = SET.INIT_VALUE[3]
        self.initialWindowSize = SET.INIT_VALUE[4]
        self.maxFrameSize = SET.INIT_VALUE[5] # octet
        self.maxHeaderListSize = SET.INIT_VALUE[6]
        self.goAwayStream_id = -1
        self.readyToPayload = False
        self.con = None

    def send(self, frame):
        self.sock.send(frame)

    def resp(self, frame):
        self.con.send(frame)

    def parseData(self, data):
        def _parseFrameHeader(data):
            return upackHex(data[:3]), data[3:4], \
                data[4:5], upackHex(data[5:9])

        def _data(data, Flag, Stream_id):
            if Stream_id == 0:
                print("err:PROTOCOL_ERROR")
            if self.streams[Stream_id] == "closed":
                print("err:STREAM_CLOSED")
            padLen = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
            content = data[1: len(data) if Flag != FLAG.PADDED else -padLen]
            print("DATA:%s" % (content))

        def _headers(data, Flag):
            index = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                padding = data[-padLen:]
                index = 1
            elif Flag == FLAG.PRIORITY:
                E = upackHex(data[:4]) & 0x80
                streamDepend = upackHex(data[:4]) & 0x7fffffff
                weight = upackHex(data[5])
                index = 5
            Wire = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
            # TODO end_headers flag should be managed with some status
            # tempral test
            self.resp(self.makeFrame(TYPE.DATA, FLAG.NO, 1, data = "aiueoDATA!!!", padLen = 0))

            print(decode(hexlify(Wire), self.table))

        def _priority(data, Stream_id):
            if Stream_id == 0:
                print("err:PROTOCOL_ERROR")
            E = upackHex(data[0]) & 0x80
            streamDependency = upackHex(data[:4]) & 0x7fffffff
            weight = upackHex(data[5])

        def _rst_stream(data, Stream_id):
            if Stream_id == 0 or self.streams[Stream_id] == "idle":
                print("err:PROTOCOL_ERROR")
            else:
                self.streams[Stream_id] = "closed"

        def _settings(data, Flag, Stream_id):
            if Stream_id != 0:
                print("err:PROTOCOL_ERROR")
            if Flag == FLAG.ACK:
                if len(data) != 0:
                    print("err:FRAME_SIZE_ERROR")
            elif len(data):
                Identifier = upackHex(data[:2])
                Value = upackHex(data[2:6])
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

        def _push_promise(data, Flag, Stream_id):
            if Stream_id == 0 or self.enablePush == 0:
                print("err:PROTOCOL_ERROR")
            if self.streams[Stream_id] != "open" and self.streams[Stream_id] != "half closed (remote)":
                print("err:PROTOCOL_ERROR")

            if Flag == FLAG.END_HEADERS:
                pass #if not, continuation frame should be come
            index = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                padding = data[-padLen:]
                index = 1
            R = upackHex(data[index]) & 0x80
            promisedStream_id = upackHex(data[index:index + 4]) & 0x7fffffff
            wire = data[index+4: len(data) if Flag != FLAG.PADDED else -padLen]
            headers = decode(hexlify(Wire))

        def _ping(data, Flag, Stream_id):
            if len(data) != 8:
                print("err:FRAME_SIZE_ERROR")
            if Stream_id != 0:
                print("err:PROTOCOL_ERROR")
            if Flag != FLAG.ACK:
                # must send ping with flag == ack
                print("ping response !")
                self.resp(self.makeFrame(TYPE.PING, FLAG.ACK, 0, ping = data[:8]))
            else:
                print("PING:%s" % (data[:8]))
                
        def _goAway(data, Stream_id):
            if Stream_id != 0:
                print("err:PROTOCOL_ERROR")
            R = upackHex(data[0]) & 0x80
            lastStreamID = upackHex(data[:4]) & 0x7fffffff
            errCode = upackHex(data[4:8])
            if len(data) > 8:
                additionalData =  upackHex(data[8:])
            self.goAwayStream_id = lastStreamID

        def _window_update(data, Stream_id):
            # not yet complete
            R = upackHex(data[0]) & 0x80
            windowSizeIncrement = upackHex(data[:4]) & 0x7fffffff
            if windowSizeIncrement == 0:
                print("err:PROTOCOL_ERROR")
            elif windowSizeIncrement >  (1 << 31) - 1:
                print("err:FLOW_CONNECTION_ERROR")
                if Stream_id == 0:
                    self.resp(self.makeFrame(TYPE.GOAWAY, err=ERR.FLOW_CONNECTION_ERROR))
                else:
                    self.resp(self.makeFrame(TYPE.RST_STREAM, err=ERR.FLOW_CONNECTION_ERROR))

        def _continuation(data ,Stream_id):
            if Stream_id == 0:
                print("err:PROTOCOL_ERROR")


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
                        _settings(data[:Length], Flags, Stream_id)
                    elif Type == TYPE.PUSH_PROMISE:
                        _push_promise(data[:Length])
                    elif Type == TYPE.PING:
                        _ping(data[:Length], Flags, Stream_id)
                    elif Type == TYPE.GOAWAY:
                        _goAway(data[:Length], Stream_id)
                    elif Type == TYPE.WINDOW_UPDATE:
                        _window_update(data[:Length], Stream_id)
                    elif Type == TYPE.CONTINUATION:
                        _continuation(data[:Length], Stream_id)
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

        def _data(flag, **kwargs):
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding += packHex(0, kwargs["padLen"])
            frame += kwargs["data"] #TODO data length should be configured
            return frame + padding

        def _headers(flag, **kwargs):
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1) # Pad Length
                padding = packHex(0, kwargs["padLen"])
            elif flag == FLAG.PRIORITY:
                streamDependency = packHex(kwargs["depend"], 4)
                if kwargs.has_key("E") and kwargs["E"]:
                    streamDependency[0] = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:])
                frame += streamDependency
                frame += packHex(kwargs["weight"], 1) # Weight
            wire = unhexlify(encode(self.headers, True, True, True, self.table))
            # continuation frame should be used if length is ~~ ?
            # should continuation frame be used from app side??
            frame += wire + padding
            return frame

        def _priority(**kwargs):
            streamDependency = packHex(kwargs["depend"], 4)
            if kwargs.has_key("E") and kwargs["E"]:
                # TODO: must fix, not cool
                streamDependency[0] = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:])
            weight = packHex(kwargs["weight"], 1)
            return streamDependency + weight

        def _rst_stream(**kwargs):
            return packHex(kwargs["err"], 4)

        def _settings(flag, **kwargs):
            if flag == FLAG.NO or flag == FLAG.ACK:
                return ""
            frame = packHex(kwargs["identifier"], 2) + packHex(kwargs["value"], 4)
            return frame

        def _push_promise(flag, **kwargs):
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding = packHex(0, kwargs["padLen"])
            elif flag == FLAG.END_HEADERS:
                pass
            # make new stream
            self.addStream()
            promisedStream_id += packHex(self.lastStream_id, 4)
            if kwargs.has_key("R") and kwargs["R"]:
                promisedStream_id[0] = unhexlify(hex(upackHex(promisedStream_id[0]) | 0x80)[2:])
            wire = unhexlify(encode(self.headers, True, True, True, self.table))
            return frame + promisedStream_id + wire + padding

        def _ping(**kwargs):
            return packHex(kwargs["ping"], 8)

        def _goAway(**kwargs):
            # R also should be here
            frame = packHex(self.lastStream_id, 4)
            frame += packHex(kwargs["err"], 4)
            frame += kwargs["debug"] if kwargs["debug"] else ""
            return frame

        def _window_update(**kwargs):
            windowSizeIncrement = packHex(kwargs["windowSizeIncrement"], 4)
            if kwargs.has_key("R") and kwargs["R"]:
                windowSizeIncrement[0] = unhexlify(hex(upackHex(windowSizeIncrement[0]) | 0x80)[2:])
            return windowSizeIncrement

        def _continuation(wire):
            # enough
            return wire

        if Type == TYPE.DATA:
            frame = _data(flag, **kwargs) # TODO  manage stream_id
        elif Type == TYPE.HEADERS:
            frame = _headers(flag, **kwargs)
        elif Type == TYPE.PRIORITY:
            frame = _priority(**kwargs)
        elif Type == TYPE.RST_STREAM:
            frame = _rst_stream(**kwargs)
        elif Type == TYPE.SETTINGS:
            frame = _settings(flag, **kwargs)
        elif Type == TYPE.PUSH_PROMISE:
            FRAME = _push_promise(flag, **kwargs)
        elif Type == TYPE.PING:
            frame = _ping(**kwargs)
        elif Type == TYPE.GOAWAY:
            frame = _goAway(**kwargs)
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
