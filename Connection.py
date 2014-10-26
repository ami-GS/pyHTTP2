from settings import *
from stream import Stream
import socket
from util import *
from binascii import unhexlify
from pyHPACK.HPACK import encode, decode


class Connection(object):
    def __init__(self, host, port, table):
        self.sock = None
        self.table = table
        self.streams = {}
        self.addStream(0)
        self.enablePush = SET.INIT_VALUE[2]
        self.maxConcurrentStreams = SET.INIT_VALUE[3]
        self.maxFrameSize = SET.INIT_VALUE[5]
        self.maxHeaderListSize = SET.INIT_VALUE[6]
        self.readyToPayload = False
        self.goAwayId = 0
        # temporaly using
        self.wireLenLimit = 24

    def send(self, frameType, flag = FLAG.NO, streamId = 0, **kwargs):
        frame = self.streams[streamId].makeFrame(frameType, flag, **kwargs)
        self.sock.send(frame)
        # here?
        while len(self.streams[streamId].wire):
            if len(self.streams[streamId].wire) > self.wireLenLimit:
                frame = self.streams[streamId].makeFrame(TYPE.CONTINUATION, FLAG.NO)
            else:
                frame = self.streams[streamId].makeFrame(TYPE.CONTINUATION, FLAG.END_HEADERS)
            self.sock.send(frame)

    def parseData(self, data):
        Length, Type, Flag, sId = 0, '\x00', '\x00', 0 #here?

        def _parseFrameHeader(data):
            return upackHex(data[:3]), data[3:4], \
                data[4:5], upackHex(data[5:9])

        def _data(data):
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            if self.streams[sId].state == ST.CLOSED:
                self.send(TYPE.RST_STREAM, streamId = sId, err = ERR.PROTOCOL_ERROR)
            if self.streams[sId].state != ST.OPEN or self.streams[sId].state != ST.HCLOSED_L:
                self.send(TYPE.RST_STREAM, streamId = sId, err = ERR.STREAM_CLOSED)
            index = 0
            padLen = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                index = 1
                if padLen > (len(data) - 1):
                    self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            elif Flag == FLAG.END_STREAM:
                if self.streams[sId].state == ST.OPEN:
                    self.streams[sId].setState(ST.HCLOSED_R)
                elif self.streams[sId].state == ST.HCLOSED_L:
                    self.streams[sId].setState(ST.CLOSED)
                #here should be refactoring
            content = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
            print("DATA:%s" % (content))

        def _headers(data):
            if self.streams[sId].state == ST.RESERVED_R:
                    self.streams[sId].setState(ST.HCLOSED_L) # suspicious
            else:
                self.streams[sId].setState(ST.OPEN)
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            index = 0
            if Flag == FLAG.END_HEADERS:
                # tempral test
                self.streams[sId].wire += data
                print(decode(hexlify(self.streams[sId].wire), self.table))
                self.send(TYPE.DATA, FLAG.NO, 1, data = "aiueoDATA!!!", padLen = 0)
                self.streams[sId].wire = ""
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
                self.streams[sId].setState(ST.HCLOSED_R)
            # Too long
            self.streams[sId].wire += data[index: len(data) if Flag != FLAG.PADDED else -padLen]

        def _priority(data):
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            E = upackHex(data[0]) & 0x80
            streamDependency = upackHex(data[:4]) & 0x7fffffff
            weight = upackHex(data[5])

        def _rst_stream(data):
            if sId == 0 or self.streams[sId].state == ST.IDLE:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            else:
                self.streams[sId].setState(ST.CLOSED)

        def _settings(data):
            # TODO: here should be wrap by try: except: ?
            if sId != 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            if Flag == FLAG.ACK:
                if Length != 0:
                    self.send(TYPE.GOAWAY, err = ERR.FRAME_SIZE_ERROR, debug = None)
            elif Length:
                Identifier = upackHex(data[:2])
                Value = upackHex(data[2:6])
                if Identifier == SET.HEADER_TABLE_SIZE:
                    self.table.setMaxHeaderTableSize(Value)
                elif Identifier == SET.ENABLE_PUSH:
                    if Value == 1 or Value == 0:
                        self.enablePush = Value
                    else:
                        self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
                elif Identifier == SET.MAX_CONCURRENT_STREAMS:
                    if Value <= 100:
                        print("Warnnig: max_concurrent_stream below 100 is not recomended")
                    self.maxConcurrentStreams = Value
                elif Identifier == SET.INITIAL_WINDOW_SIZE:
                    if Value > MAX_WINDOW_SIZE:
                        self.send(TYPE.GOAWAY, err = ERR.FLOW_CONTOROL_ERROR, debug = None)
                    else:
                        self.windowSize = Value
                elif Identifier == SET.MAX_FRAME_SIZE:
                    if INITIAL_MAX_FRAME_SIZE <= Value  <= LIMIT_MAX_FRAME_SIZE:
                        self.maxFrameSize = Value
                    else:
                        self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
                elif Identifier == SET.MAX_HEADER_LIST_SIZE:
                    self.maxHeaderListSize = Value # ??
                else:
                    pass # must ignore
                # must send ack
                self.send(TYPE.SETTINGS, FLAG.ACK, 0, ident=SET.NO, value = "")

        def _push_promise(data):
            if sId == 0 or self.enablePush == 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            if self.streams[sId].state != ST.OPEN and self.streams[sId].state != ST.HCLOSED_L:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)

            index = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                padding = data[-padLen:]
                index = 1
            R = upackHex(data[index]) & 0x80
            promisedId = upackHex(data[index:index + 4]) & 0x7fffffff
            self.addStream(promisedId, ST.RESERVED_R)
            # TODO: here should be optimised
            self.streams[sId].wire += data[index+4: len(data) if Flag != FLAG.PADDED else -padLen]
            if Flag == FLAG.END_HEADERS:
                print(decode(hexlify(self.streams[sId].wire), self.table))
                self.streams[sId].wire = ""

        def _ping(data):
            if Length != 8:
                self.send(TYPE.GOAWAY, err = ERR.FRAME_SIZE_ERROR, debug = None)
            if sId != 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            if Flag != FLAG.ACK:
                print("ping response !")
                self.send(TYPE.PING, FLAG.ACK, 0, ping = data)
            else:
                print("PING:%s" % (data))

        def _goAway(data):
            if sId != 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            R = upackHex(data[0]) & 0x80
            lastStreamID = upackHex(data[:4]) & 0x7fffffff
            errCode = upackHex(data[4:8])
            if len(data) > 8:
                additionalData =  upackHex(data[8:])
            self.goAwaysId = lastStreamID

        def _window_update(data):
            # not yet complete
            R = upackHex(data[0]) & 0x80
            windowSizeIncrement = upackHex(data[:4]) & 0x7fffffff
            if windowSizeIncrement == 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            elif windowSizeIncrement >  (1 << 31) - 1:
                # is this correct ?
                if sId == 0:
                    self.send(TYPE.GOAWAY, err=ERR.FLOW_CONNECTION_ERROR)
                else:
                    self.send(TYPE.RST_STREAM, err=ERR.FLOW_CONNECTION_ERROR)

        def _continuation(data):
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR.PROTOCOL_ERROR, debug = None)
            self.streams[sId].wire += data
            if Flag == FLAG.END_HEADERS:
                print(decode(hexlify(self.streams[sId].wire), self.table))
                # ready to response status should be made
                # issue:  this cause sender print(decode(wire)) TODO: must be fixed
                #self.send(TYPE.DATA, FLAG.NO, 1, data = "aiueoDATA!!!", padLen = 0)
                self.streams[sId].wire = ""

        if self.goAwayId and self.goAwayId < sId:
            # must ignore
            return
        while len(data) or Type == TYPE.SETTINGS:
            if data.startswith(CONNECTION_PREFACE):
                #send settings (this may be empty)
                data = data.lstrip(CONNECTION_PREFACE)
            else:
                print(Length, hexlify(Type), hexlify(Flag), sId, self.readyToPayload)
                if self.readyToPayload:
                    if Type == TYPE.DATA:
                        _data(data[:Length])
                    elif Type == TYPE.HEADERS:
                        _headers(data[:Length])
                    elif Type == TYPE.PRIORITY:
                        _priority(data[:Length])
                    elif Type == TYPE.RST_STREAM:
                        _rst_stream(data[:Length])
                    elif Type == TYPE.SETTINGS:
                        _settings(data[:Length])
                    elif Type == TYPE.PUSH_PROMISE:
                        _push_promise(data[:Length])
                    elif Type == TYPE.PING:
                        _ping(data[:Length])
                    elif Type == TYPE.GOAWAY:
                        _goAway(data[:Length])
                    elif Type == TYPE.WINDOW_UPDATE:
                        _window_update(data[:Length])
                    elif Type == TYPE.CONTINUATION:
                        _continuation(data[:Length])
                    else:
                        print("err:undefined frame type",Type)
                    data = data[Length:]
                    Length, Type, Flag, sId = 0, '\x00', '\x00', 0 #here?
                    self.readyToPayload = False
                else:
                    Length, Type, Flag, sId = _parseFrameHeader(data)

                    if not self.streams.has_key(sId):
                        self.addStream(sId) # this looks strange
                    if self.streams[sId].state == ST.CLOSED and Type != TYPE.PRIORITY:
                        self.send(TYPE.RST_STREAM, err=ERR.STREAM_CLOSED)
                    #print(hexlify(data))
                    #print(Length, hexlify(Type), hexlify(Flag), sId, "set")
                    data = data[FRAME_HEADER_SIZE:]
                    self.readyToPayload = True

    def setTable(self, table):
        self.table = table

    def setHeaders(self, headers):
        self.headers = headers

    def addStream(self, stream, state = ST.IDLE):
        self.streams[stream] = Stream(stream, self, state)

class Server(Connection):
    def __init__(self, host, port, table = None):
        super(Server, self).__init__(host, port, table)
        self.serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lastId = 2
        self.serv.bind((host, port))
        self.addStream(self.lastId)

    def runServer(self):
        self.serv.listen(1) # number ?
        while True:
            print("Connection waiting...")
            self.sock, addr = self.serv.accept()
            data = "dummy"
            while len(data):
                data = self.sock.recv((self.maxFrameSize + FRAME_HEADER_SIZE) * 8) # here should use window length ?
                self.parseData(data)

class Client(Connection):
    def __init__(self, host, port, table = None):
        super(Client, self).__init__(host, port, table)
        self.lastId = 1
        self.addStream(self.lastId)
        self.sock = socket.create_connection((host, port), 5)

    def notifyHTTP2(self):
        self.sock.send(CONNECTION_PREFACE)
