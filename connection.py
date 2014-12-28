from settings import *
from stream import Stream
import socket
from util import *
from pyHPACK.HPACK import decode
from pyHPACK.tables import Table

class Connection(object):
    def __init__(self, sock, addr, enable_tls, debug):
        self.setSocket(sock, enable_tls)
        self.addr = addr
        self.table = Table()
        self.streams = {}
        self.enablePush = SETTINGS.INIT_VALUE["enable_push"]
        self.maxConcurrentStreams = SETTINGS.INIT_VALUE["concurrent_streams"]
        self.maxFrameSize = SETTINGS.INIT_VALUE["frame_size"]
        self.maxHeaderListSize = SETTINGS.INIT_VALUE["header_list_size"]
        self.initialWindowSize = SETTINGS.INIT_VALUE["window_size"]
        self.readyToPayload = False
        self.goAwayId = 0
        self.addStream(0)
        # temporaly using
        self.wireLenLimit = 24
        self.debug = debug

    def setSocket(self, sock, enable_tls):
        self.sock = sock
        if enable_tls:
            self._send = sock.write
            self._recv = sock.read
        else:
            self._send = sock.send
            self._recv = sock.recv

    def _send(self):
        pass

    def _recv(self):
        pass

    def send(self, frameType, flag = FLAG.NO, streamId = 0, **kwargs):
        frame = self.streams[streamId].makeFrame(frameType, flag, **kwargs)
        self._send(frame)
        # here?
        while len(self.streams[streamId].wire):
            if len(self.streams[streamId].wire) > self.wireLenLimit:
                frame = self.streams[streamId].makeFrame(TYPE.CONTINUATION, FLAG.NO)
            else:
                frame = self.streams[streamId].makeFrame(TYPE.CONTINUATION, FLAG.END_HEADERS)
            self._send(frame)

    def parseData(self, data):
        Length, Type, Flag, sId = 0, '\x00', '\x00', 0 #here?

        def _parseFrameHeader(data):
            return upackHex(data[:3]), data[3:4], \
                data[4:5], upackHex(data[5:9])

        def _data(data):
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            if self.streams[sId].state == STATE.CLOSED:
                self.send(TYPE.RST_STREAM, streamId = sId, err = ERR_CODE.PROTOCOL_ERROR)
            if self.streams[sId].state != STATE.OPEN and self.streams[sId].state != STATE.HCLOSED_L:
                self.send(TYPE.RST_STREAM, streamId = sId, err = ERR_CODE.STREAM_CLOSED)
            index = 0
            padLen = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                index = 1
                if padLen > (len(data) - 1):
                    self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            elif Flag == FLAG.END_STREAM:
                if self.streams[sId].state == STATE.OPEN:
                    self.streams[sId].setState(STATE.HCLOSED_R)
                elif self.streams[sId].state == STATE.HCLOSED_L:
                    self.streams[sId].setState(STATE.CLOSED)
                #here should be refactoring
            # if padding != 0 then send protocol_error (MAY)
            content = data[index: len(data) if Flag != FLAG.PADDED else -padLen]
            self.streams[sId].decreaseWindow(len(content) * 8)
            print("DATA:%s" % (content))

        def _headers(data):
            if self.streams[sId].state == STATE.RESERVED_R:
                    self.streams[sId].setState(STATE.HCLOSED_L) # suspicious
            else:
                self.streams[sId].setState(STATE.OPEN)
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)

            index = 0
            if Flag == FLAG.END_HEADERS:
                # tempral test
                print(decode(hexlify(data), self.table))
                self.send(TYPE.DATA, FLAG.END_STREAM, 1, data = "aiueoDATA!!!", padLen = 0)
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
                self.streams[sId].setState(STATE.HCLOSED_R)
            # Too long
            self.streams[sId].wire += data[index: len(data) if Flag != FLAG.PADDED else -padLen]

        def _priority(data):
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            if Length != 5:
                self.send(TYPE.GOAWAY, err = ERR_CODE.FRAME_SIZE_ERROR, debug = None)
            E = upackHex(data[0]) & 0x80
            streamDependency = upackHex(data[:4]) & 0x7fffffff
            weight = upackHex(data[4])

        def _rst_stream(data):
            if Length != 4:
                self.send(TYPE.GOAWAY, err = ERR_CODE.FRAME_SIZE_ERROR, debug = None)
            if sId == 0 or self.streams[sId].state == STATE.IDLE:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            else:
                num = upackHex(data)
                if self.debug:
                    print("RST STREAM: %s" % ERR_CODE.string(num))
                self.streams[sId].setState(STATE.CLOSED)

        def _settings(data):
            # TODO: here should be wrap by try: except: ?
            if sId != 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            if Length % 6 != 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.FRAME_SIZE_ERROR, debug = None)
            if Flag == FLAG.ACK:
                if Length != 0:
                    self.send(TYPE.GOAWAY, err = ERR_CODE.FRAME_SIZE_ERROR, debug = None)
            elif Length:
                param = upackHex(data[:2])
                value = upackHex(data[2:6])
                if param == SETTINGS.HEADER_TABLE_SIZE:
                    self.setHeaderTableSize(value)
                elif param == SETTINGS.ENABLE_PUSH:
                    if value == 1 or value == 0:
                        self.enablePush = value
                    else:
                        self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
                elif param == SETTINGS.MAX_CONCURRENT_STREAMS:
                    if value <= 100:
                        print("Warnnig: max_concurrent_stream below 100 is not recomended")
                    self.maxConcurrentStreams = value
                elif param == SETTINGS.INITIAL_WINDOW_SIZE:
                    if value > MAX_WINDOW_SIZE:
                        self.send(TYPE.GOAWAY, err = ERR_CODE.FLOW_CONTOROL_ERROR, debug = None)
                    else:
                        self.initialWindowSize = value
                elif param == SETTINGS.MAX_FRAME_SIZE:
                    if INITIAL_MAX_FRAME_SIZE <= value  <= LIMIT_MAX_FRAME_SIZE:
                        self.maxFrameSize = value
                    else:
                        self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
                elif param == SETTINGS.MAX_HEADER_LIST_SIZE:
                    self.maxHeaderListSize = value # ??
                else:
                    pass # must ignore
                # must send ack
                self.send(TYPE.SETTINGS, FLAG.ACK, 0, param=SETTINGS.NO, value = "")

        def _push_promise(data):
            if sId == 0 or self.enablePush == 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            if self.streams[sId].state != STATE.OPEN and self.streams[sId].state != STATE.HCLOSED_L:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)

            index = 0
            if Flag == FLAG.PADDED:
                padLen = upackHex(data[0])
                padding = data[-padLen:]
                index = 1
            R = upackHex(data[index]) & 0x80
            promisedId = upackHex(data[index:index + 4]) & 0x7fffffff
            self.addStream(promisedId, STATE.RESERVED_R)
            # TODO: here should be optimised
            tmp = data[index+4: len(data) if Flag != FLAG.PADDED else -padLen]
            if Flag == FLAG.END_HEADERS:
                print(decode(hexlify(tmp), self.table))
            else:
                self.streams[sId].wire += tmp

        def _ping(data):
            if Length != 8:
                self.send(TYPE.GOAWAY, err = ERR_CODE.FRAME_SIZE_ERROR, debug = None)
            if sId != 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            if Flag != FLAG.ACK:
                print("ping response !")
                self.send(TYPE.PING, FLAG.ACK, 0, ping = data)
            else:
                print("PING:%s" % (data))

        def _goAway(data):
            if sId != 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            R = upackHex(data[0]) & 0x80
            lastStreamID = upackHex(data[:4]) & 0x7fffffff
            errCode = upackHex(data[4:8])
            if self.debug:
                print("GO AWAY: %s" % ERR_CODE.string(errCode))
            if len(data) > 8:
                additionalData =  upackHex(data[8:])
            self.goAwaysId = lastStreamID

        def _window_update(data):
            # not yet complete
            if Length != 4:
                self.send(TYPE.GOAWAY, err = ERR_CODE.FRAME_SIZE_ERROR, debug = None)
            R = upackHex(data[0]) & 0x80
            windowSizeIncrement = upackHex(data[:4]) & 0x7fffffff
            if windowSizeIncrement <= 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
            elif windowSizeIncrement >  (1 << 31) - 1:
                # is this correct ?
                if sId == 0:
                    self.send(TYPE.GOAWAY, err=ERR_CODE.FLOW_CONNECTION_ERROR)
                else:
                    self.send(TYPE.RST_STREAM, streamId = sId, err=ERR_CODE.FLOW_CONNECTION_ERROR)
            else:
                self.streams[sId].setWindowSize(windowSizeIncrement)

        def _continuation(data):
            if sId == 0:
                self.send(TYPE.GOAWAY, err = ERR_CODE.PROTOCOL_ERROR, debug = None)
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
                if self.readyToPayload:
                    print(Length, TYPE.string(Type), FLAG.string(Flag), sId, self.readyToPayload)
                    if self.streams[sId].state == STATE.CLOSED and \
                       Type != TYPE.PRIORITY and Type != TYPE.RST_STREAM:
                        self.send(TYPE.RST_STREAM, streamId = sId, err=ERR_CODE.STREAM_CLOSED)
                    else:
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
                    data = data[FRAME_HEADER_SIZE:]
                    self.readyToPayload = True

    def addStream(self, stream, state = STATE.IDLE):
        self.streams[stream] = Stream(stream, self, state)

    def setHeaderTableSize(self, size):
        self.table.setMaxHeaderTableSize(size)
