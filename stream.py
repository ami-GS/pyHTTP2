from settings import *
from util import *
from binascii import unhexlify
from pyHPACK.HPACK import encode

class Stream():
    def __init__(self, stream_id, connection, state):
        self.sId = stream_id
        self.connection = connection
        self.state = state
        self.windowSize = self.connection.initialWindowSize
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
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding += packHex(0, kwargs["padLen"])
            elif flag == FLAG.END_STREAM:
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
                self.wire = unhexlify(encode(kwargs["headers"], False, False, False, self.connection.table))
                # not cool, should be optimised
                if len(self.wire) <= self.connection.wireLenLimit:
                    self.flag = FLAG.END_HEADERS
            if self.state == STATE.RESERVED_L:
                self.setState(STATE.HCLOSED_R) # suspicious
            self.setState(STATE.OPEN) # here?
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1) # Pad Length
                padding = packHex(0, kwargs["padLen"])
            elif flag == FLAG.PRIORITY:
                streamDependency = packHex(kwargs["depend"], 4)
                if kwargs.has_key("E") and kwargs["E"]:
                    streamDependency = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:]) + streamDependency[1:]
                frame += streamDependency
                frame += packHex(kwargs["weight"], 1) # Weight
            elif flag == FLAG.END_HEADERS:
                self.setState(STATE.HCLOSED_L)
            elif flag == FLAG.END_STREAM:
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
            if flag == FLAG.NO or flag == FLAG.ACK:
                return ""

            frame = packHex(kwargs["param"], 2) + packHex(kwargs["value"], 4)
            return frame

        def _push_promise():
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding = packHex(0, kwargs["padLen"])
            if kwargs.has_key("headers"):
                self.wire = unhexlify(encode(kwargs["headers"], False, False, False, self.connection.table))
                # not cool, should be optimised
                if len(self.wire) <= self.connection.wireLenLimit:
                    self.flag = FLAG.END_HEADERS
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
