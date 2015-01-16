from settings import *
from util import *
from binascii import unhexlify
from pyHPACK.HPACK import encode

class Stream():
    def __init__(self, stream_id, connection, state):
        self.sId = stream_id
        self.connection = connection
        self.state = state
        self.windowSize = connection.initialWindowSize
        self.wire = ""

    def setWindowSize(self, windowSize):
        self.windowSize = windowSize

    def decreaseWindow(self, size):
        self.windowSize -= size

    def setState(self, state):
        self.state = state

    def appendWire(self, wire):
        self.wire += wire

    def getWire(self):
        return self.wire

    def makeFrame(self, fType, flag, **kwargs):
        self.flag = flag # temporaly using
        def _HTTP2Frame(length):
            return packHex(length, 3) + packHex(fType, 1) + packHex(self.flag, 1) + packHex(self.sId, 4)

        def _data():
            frame = ""
            padding = ""
            if flag&FLAG.PADDED == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding += packHex(0, kwargs["padLen"])
            if flag&FLAG.END_STREAM == FLAG.END_STREAM:
                if self.state == STATE.OPEN:
                    self.setState(STATE.HCLOSED_L)
                elif self.state == STATE.HCLOSED_R:
                    self.setState(STATE.CLOSED)
            frame += kwargs["data"] + padding #TODO data length should be configured
            self.decreaseWindow(len(frame) * 8)
            return frame

        def _headers():
            frame = ""
            padding = ""
            if kwargs.has_key("headers"):
                self.wire = encode(kwargs["headers"], False, False, False, self.connection.table)
                # not cool, should be optimised
                if len(self.wire) <= self.connection.wireLenLimit:
                    self.flag |= FLAG.END_HEADERS
            if self.state == STATE.RESERVED_L:
                self.setState(STATE.HCLOSED_R) # suspicious
            self.setState(STATE.OPEN) # here?
            if flag&FLAG.PADDED == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1) # Pad Length
                padding = packHex(0, kwargs["padLen"])
            if flag&FLAG.PRIORITY == FLAG.PRIORITY:
                streamDependency = packHex(kwargs["depend"], 4)
                if kwargs.has_key("E") and kwargs["E"]:
                    streamDependency = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:]) + streamDependency[1:]
                frame += streamDependency
                frame += packHex(kwargs["weight"], 1) # Weight
            if self.flag&FLAG.END_HEADERS == FLAG.END_HEADERS:
                self.setState(STATE.HCLOSED_L)
            if flag&FLAG.END_STREAM == FLAG.END_STREAM:
                self.setState(STATE.HCLOSED_L)
            # TODO: wire len limit should be configured properly
            if len(self.wire) > self.connection.wireLenLimit:
                frame += self.wire[:self.connection.wireLenLimit] + padding
                self.wire = self.wire[self.connection.wireLenLimit:]
            else:
                frame += self.wire + padding
                self.wire = ""
            return frame

        def _priority():
            streamDependency = packHex(kwargs["depend"], 4)
            if kwargs.has_key("E") and kwargs["E"]:
                # TODO: must fix, not cool
                streamDependency = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:]) + streamDependency[1:]
            weight = packHex(kwargs["weight"], 1)
            return streamDependency + weight

        def _rst_stream():
            self.setState(STATE.CLOSED)
            return packHex(kwargs["err"], 4)

        def _settings():
            if flag == FLAG.ACK:
                return ""

            param = kwargs["param"] #TODO: this is danger
            value = kwargs["value"]
            if param == SETTINGS.HEADER_TABLE_SIZE:
                self.connection.setHeaderTableSize(value)
            elif param == SETTINGS.ENABLE_PUSH:
                # suspicious
                if value == 1 or value == 0:
                    self.connection.enablePush = value
                else:
                    pass #should emit warnnig
            elif param == SETTINGS.MAX_CONCURRENT_STREAMS:
                if value <= 100:
                    print("Warnnig: max_concurrent_stream below 100 is not recomended")
                self.connection.maxConcurrentStreams = value
            elif param == SETTINGS.INITIAL_WINDOW_SIZE:
                if value > MAX_WINDOW_SIZE:
                    pass #should emit warnning
                else:
                    self.connection.initialWindowSize = value
            elif param == SETTINGS.MAX_FRAME_SIZE:
                if INITIAL_MAX_FRAME_SIZE <= value <= LIMIT_MAX_FRAME_SIZE:
                    self.connection.maxFrameSize = value
                else:
                    pass #shoule emit warnning
            elif param == SETTINGS.MAX_HEADER_LIST_SIZE:
                self.connection.maxHeaderListSize = value # ??
            else:
                pass #should emit warnning

            frame = packHex(param, 2) + packHex(value, 4)
            return frame

        def _push_promise():
            frame = ""
            padding = ""
            if flag&FLAG.PADDED == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding = packHex(0, kwargs["padLen"])
            if kwargs.has_key("headers"):
                self.wire = encode(kwargs["headers"], False, False, False, self.connection.table)
                # not cool, should be optimised
                if len(self.wire) <= self.connection.wireLenLimit:
                    self.flag |= FLAG.END_HEADERS
            # make new stream
            promisedId = packHex(kwargs["pushId"], 4)
            self.connection.addStream(kwargs["pushId"], STATE.RESERVED_L)
            if kwargs.has_key("R") and kwargs["R"]:
                promisedId = unhexlify(hex(upackHex(promisedId[0]) | 0x80)[2:]) + promisedId[1:]

            if len(self.wire) > self.connection.wireLenLimit:
                wire = self.wire[:self.connection.wireLenLimit] + padding
                self.wire = self.wire[self.connection.wireLenLimit:]
            else:
                wire = self.wire + padding
                self.wire = ""

            return frame + promisedId + wire

        def _ping():
            return packHex(kwargs["ping"], 8)

        def _goAway():
            # R also should be here
            frame = packHex(self.connection.lastId, 4)
            frame += packHex(kwargs["err"], 4)
            frame += kwargs["debug"] if kwargs["debug"] else ""
            return frame

        def _window_update():
            windowSizeIncrement = packHex(kwargs["windowSizeIncrement"], 4)
            self.setWindowSize(kwargs["windowSizeIncrement"])
            if kwargs.has_key("R") and kwargs["R"]:
                windowSizeIncrement = unhexlify(hex(upackHex(windowSizeIncrement[0]) | 0x80)[2:]) + windowSizeIncrement[1:]
            return windowSizeIncrement

        def _continuation():
            frame = self.wire[:self.connection.wireLenLimit]
            self.wire = self.wire[self.connection.wireLenLimit:]
            return frame

        if fType == TYPE.DATA:
            frame = _data() # TODO  manage stream_id
        elif fType == TYPE.HEADERS:
            frame = _headers()
        elif fType == TYPE.PRIORITY:
            frame = _priority()
        elif fType == TYPE.RST_STREAM:
            frame = _rst_stream()
        elif fType == TYPE.SETTINGS:
            frame = _settings()
        elif fType == TYPE.PUSH_PROMISE:
            frame = _push_promise()
        elif fType == TYPE.PING:
            frame = _ping()
        elif fType == TYPE.GOAWAY:
            frame = _goAway()
        elif fType == TYPE.WINDOW_UPDATE:
            frame = _window_update()
        elif fType == TYPE.CONTINUATION:
            frame = _continuation()
        else:
            print("err:undefined frame type", fType)
        http2Frame = _HTTP2Frame(len(frame))
        return http2Frame + frame
