from pyHPACK.HPACK import encode, decode
from settings import *
import socket
from binascii import hexlify, unhexlify

FLAG = BaseFlag
TYPE = FrameType
SET = Settings
ERR = ErrorCode
ST = State

def packHex(val, l):
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

def upackHex(val):
    return int(hexlify(val), 16)

class HTTP2Base(object):
    def __init__(self, host, port, table = None):
        self.table = table
        self.host, self.port = host, port
        self.lastsId = None
        # TODO: should previous frame be implemented for header next to it which has END_HEADER flag
        #self.streams = {0:{"state":"open", "header":[True, ""]}} # stream_id, status, header flagment
        self.streams = {0:INITIAL_STREAM_STATE}
        self.enablePush = SET.INIT_VALUE[2]
        self.maxConcurrentStreams = SET.INIT_VALUE[3]
        self.windowSize = SET.INIT_VALUE[4]
        self.maxFrameSize = SET.INIT_VALUE[5] # octet
        self.maxHeaderListSize = SET.INIT_VALUE[6]
        self.goAwaysId = -1
        self.readyToPayload = False

    def send(self, frame):
        self.sock.send(frame)

    def setState(self, state, sId):
        self.streams[sId][state] = state

    def parseData(self, data):
        def _parseFrameHeader(data):
            return upackHex(data[:3]), data[3:4], \
                data[4:5], upackHex(data[5:9])

        def _data(data, Flag, sId):
            if sId == 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            if self.streams[sId]["state"] == ST.CLOSED:
                self.send(self.makeFrame(TYPE.RST_STREAM, err = ERR.PROTOCOL_ERROR))
            index = 0
            padLen = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                index = 1
                if padLen > (len(data) - 1):
                    self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            elif Flag == FLAG.END_STREAM:
                if self.streams[sId]["state"] == ST.OPEN:
                    self.setState(ST.HCLOSED_R, sId)
                elif self.streams[sId]["state"] == ST.HCLOSED_L:
                    self.setState(ST.CLOSED, sId)
                #here should be refactoring
            content = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
            print("DATA:%s" % (content))

        def _headers(data, Flag, sId):
            if self.streams[sId]["state"] == ST.RESERVED_R:
                    self.setState(ST.HCLOSED_L, sId) # suspicious
            else:
                self.setState(ST.OPEN, sId)
            if sId == 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            index = 0
            if Flag == FLAG.END_HEADERS:
                # tempral test
                self.streams[sId]["header"][1] += data # Padding is unclear
                print(decode(hexlify(self.streams[sId]["header"][1]), self.table))
                self.send(self.makeFrame(TYPE.DATA, FLAG.NO, 1, data = "aiueoDATA!!!", padLen = 0))
                self.streams[sId]["header"] = [True, ""] # init header in a stream
                return
            elif Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                padding = data[-padLen:]
                index = 1
            elif Flag == FLAG.PRIORITY:
                E = upackHex(data[:4]) & 0x80
                streamDepend = upackHex(data[:4]) & 0x7fffffff
                weight = upackHex(data[5])
                index = 5
            elif Flag == FLAG.END_STREAM:
                self.setState(ST.HCLOSED_R, sId)
            # Too long
            self.streams[sId]["header"][1] += data[index: len(data) if Flag != FLAG.PADDED else -padLen]
            self.streams[sId]["header"][0] = False

        def _priority(data, sId):
            if sId == 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            E = upackHex(data[0]) & 0x80
            streamDependency = upackHex(data[:4]) & 0x7fffffff
            weight = upackHex(data[5])

        def _rst_stream(data, sId):
            if sId == 0 or self.streams[sId]["state"] == ST.IDLE:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            else:
                self.setState(ST.CLOSED, sId)

        def _settings(data, Flag, sId):
            if sId != 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            if Flag == FLAG.ACK:
                if len(data) != 0:
                    self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.FRAME_SIZE_ERROR, debug = None))
            elif len(data):
                Identifier = upackHex(data[:2])
                Value = upackHex(data[2:6])
                if Identifier == SET.HEADER_TABLE_SIZE:
                    self.table.setMaxHeaderTableSize(Value)
                elif Identifier == SET.ENABLE_PUSH:
                    if Value == 1 or Value == 0:
                        self.enablePush = Value
                    else:
                        self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
                elif Identifier == SET.MAX_CONCURRENT_STREAMS:
                    if Value < 100:
                        print("Warnnig: max_concurrent_stream below 100 is not recomended")
                    self.maxConcurrentStreams = Value
                elif Identifier == SET.INITIAL_WINDOW_SIZE:
                    if Value > MAX_WINDOW_SIZE:
                        self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.FLOW_CONTOROL_ERROR, debug = None))
                    else:
                        self.windowSize = Value
                elif Identifier == SET.MAX_FRAME_SIZE:
                    if INITIAL_MAX_FRAME_SIZE <= Value  <= LIMIT_MAX_FRAME_SIZE:
                        self.maxFrameSize = Value
                    else:
                        self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
                elif Identifier == SET.MAX_HEADER_LIST_SIZE:
                    self.maxHeaderListSize = Value # ??
                else:
                    pass # must ignore
                # must send ack
                self.send(self.makeFrame(TYPE.SETTINGS, FLAG.ACK, 0, ident=SET.NO, value = ""))

        def _push_promise(data, Flag, sId):
            if sId == 0 or self.enablePush == 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            if self.streams[sId]["state"] != ST.OPEN and self.streams[sId]["state"] != ST.HCLOSED_R:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            self.setState(ST.RESERVED_R, sId)
            index = 0
            if Flag == FLAG.END_HEADERS:
                self.streams[sId]["header"][1] += data[index+4:] # TODO:There may be padding?
                self.streams[sId]["header"] = [True, ""] # TODO:is this needed? header should be decoded
            elif Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                padding = data[-padLen:]
                index = 1
            R = upackHex(data[index]) & 0x80
            promisedsId = upackHex(data[index:index + 4]) & 0x7fffffff
            self.streams[sId]["header"][1] += data[index+4: len(data) if Flag != FLAG.PADDED else -padLen]
            self.streams[sId]["header"][0] = False

        def _ping(data, Flag, sId):
            if len(data) != 8:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            if sId != 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            if Flag != FLAG.ACK:
                print("ping response !")
                self.send(self.makeFrame(TYPE.PING, FLAG.ACK, 0, ping = data[:8]))
            else:
                print("PING:%s" % (data[:8]))

        def _goAway(data, sId):
            if sId != 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            R = upackHex(data[0]) & 0x80
            lastStreamID = upackHex(data[:4]) & 0x7fffffff
            errCode = upackHex(data[4:8])
            if len(data) > 8:
                additionalData =  upackHex(data[8:])
            self.goAwaysId = lastStreamID

        def _window_update(data, sId):
            # not yet complete
            R = upackHex(data[0]) & 0x80
            windowSizeIncrement = upackHex(data[:4]) & 0x7fffffff
            if windowSizeIncrement == 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            elif windowSizeIncrement >  (1 << 31) - 1:
                # is this correct ?
                if sId == 0:
                    self.send(self.makeFrame(TYPE.GOAWAY, err=ERR.FLOW_CONNECTION_ERROR))
                else:
                    self.send(self.makeFrame(TYPE.RST_STREAM, err=ERR.FLOW_CONNECTION_ERROR))

        def _continuation(data, Flag, sId):
            if sId == 0:
                self.send(self.makeFrame(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None))
            self.streams[sId]["header"] += data

            if Flag == FLAG.END_HEADERS:
                print(decode(hexlify(self.streams[sId]["header"][1]), self.table))
                # ready to response status should be made
                self.send(self.makeFrame(TYPE.DATA, FLAG.NO, 1, data = "aiueoDATA!!!", padLen = 0))
                self.streams[sId]["header"] = [True, ""]

        Length, Type, Flags, sId = 0, '\x00', '\x00', 0 #here?
        while len(data) or Type == TYPE.SETTINGS:
            if data.startswith(CONNECTION_PREFACE):
                #send settings (this may be empty)
                data = data.lstrip(CONNECTION_PREFACE)
            else:
                print(Length, hexlify(Type), hexlify(Flags), sId, self.readyToPayload)
                if self.readyToPayload:
                    if Type == TYPE.DATA:
                        _data(data[:Length], Flags, sId)
                    elif Type == TYPE.HEADERS:
                        _headers(data[:Length], Flags, sId)
                    elif Type == TYPE.PRIORITY:
                        _priority(data[:Length])
                    elif Type == TYPE.RST_STREAM:
                        _rst_stream(data[:Length])
                    elif Type == TYPE.SETTINGS:
                        _settings(data[:Length], Flags, sId)
                    elif Type == TYPE.PUSH_PROMISE:
                        _push_promise(data[:Length])
                    elif Type == TYPE.PING:
                        _ping(data[:Length], Flags, sId)
                    elif Type == TYPE.GOAWAY:
                        _goAway(data[:Length], sId)
                    elif Type == TYPE.WINDOW_UPDATE:
                        _window_update(data[:Length], sId)
                    elif Type == TYPE.CONTINUATION:
                        _continuation(data[:Length], sId)
                    else:
                        print("err:undefined frame type",Type)
                    data = data[Length:]
                    Length, Type, Flags, sId = 0, '\x00', '\x00', 0 #here?
                    self.readyToPayload = False
                else:
                    Length, Type, Flags, sId = _parseFrameHeader(data)

                    if not self.streams.has_key(sId):
                        self.addStream(sId) # this looks strange
                    if self.streams[sId]["state"] == ST.CLOSED and Type != TYPE.PRIORITY:
                        self.send(self.makeFrame(TYPE.RST_STREAM, err=ERR.STREAM_CLOSED))
                    print(hexlify(data))
                    print(Length, hexlify(Type), hexlify(Flags), sId, "set")
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
            elif flag == FLAG.END_STREAM:
                if self.streams[sId]["state"] == ST.OPEN:
                    self.setState(ST.HCLOSED_L, sId)
                elif self.streams[sId]["state"] == ST.HCLOSED_R:
                    self.setState(ST.CLOSED, sId)
            frame += kwargs["data"] #TODO data length should be configured
            return frame + padding

        def _headers(flag, **kwargs):
            frame = ""
            padding = ""
            if self.streams[stream_id]["state"] == ST.RESERVED_L:
                self.setState(ST.HCLOSED_R, sId) # suspicious
            self.setState(ST.OPEN, stream_id) # here?
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1) # Pad Length
                padding = packHex(0, kwargs["padLen"])
            elif flag == FLAG.PRIORITY:
                streamDependency = packHex(kwargs["depend"], 4)
                if kwargs.has_key("E") and kwargs["E"]:
                    streamDependency[0] = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:])
                frame += streamDependency
                frame += packHex(kwargs["weight"], 1) # Weight
            elif flag == FLAG.END_HEADERS:
                self.setState(ST.HCLOSED_L, stream_id)
            elif flag == FLAG.END_STREAM:
                self.setState(ST.HCLOSED_L, stream_id)

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
            self.setState(ST.CLOSED, stream_id)
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
            self.setState(ST.RESERVED_L, stream_id)
            self.addStream()
            promisedsId += packHex(self.lastsId, 4)
            if kwargs.has_key("R") and kwargs["R"]:
                promisedsId[0] = unhexlify(hex(upackHex(promisedsId[0]) | 0x80)[2:])
            wire = unhexlify(encode(self.headers, True, True, True, self.table))
            return frame + promisedsId + wire + padding

        def _ping(**kwargs):
            return packHex(kwargs["ping"], 8)

        def _goAway(**kwargs):
            # R also should be here
            frame = packHex(self.lastsId, 4)
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

    def addStream(self, sId = 0):
        if sId:
            self.streams[sId] = INITIAL_STREAM_STATE
        else:
            self.lastsId += 2
            self.streams[self.lastsId] = INITIAL_STREAM_STATE

    def setTable(self, table):
        self.table = table

    def setHeaders(self, headers):
        self.headers = headers

class Server(HTTP2Base):
    def __init__(self, host, port, table = None):
        super(Server, self).__init__(host, port, table)
        self.serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lastsId = 2
        self.streams[self.lastsId] = INITIAL_STREAM_STATE

    def runServer(self):
        self.serv.bind((self.host, self.port))
        self.serv.listen(1) # number ?
        while True:
            print("Connection waiting...")
            self.sock, addr = self.serv.accept()
            data = "dummy"
            while len(data):
                data = self.sock.recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8) # here should use window length ?
                self.parseData(data)

class Client(HTTP2Base):
    def __init__(self, host, port, table = None):
        super(Client, self).__init__(host, port, table)
        self.lastsId = 1
        self.streams[self.lastsId] = INITIAL_STREAM_STATE
        self.sock = socket.create_connection((host, port), 5)
