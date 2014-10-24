from settings import *
from util import *


class Stream():
    def __init__(self, stream_id, connection, state):
        self.sId = stream_id
        self.connection = connection
        self.state = state
        self.windowSize = Settings.INIT_VALUE[4]
        self.Wire = ""
        self.finWire = True

    def setWindowSize(self, windowSize):
        self.windowSize = windowSize

    def setState(self, state):
        self.state = state

    def appendWire(self, wire):
        self.wire += wire

    def getWire(self):
        return self.wire

    def makeFrame(self, fType, flag, **kwargs):
        def _HTTP2Frame(length):
            return packHex(length, 3) + packHex(fType, 1) + packHex(flag, 1) + packHex(self.sId, 4)

        def _data():
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding += packHex(0, kwargs["padLen"])
            elif flag == FLAG.END_STREAM:
                if self.state == ST.OPEN:
                    self.setState(ST.HCLOSED_L)
                elif self.state == ST.HCLOSED_R:
                    self.setState(ST.CLOSED)
            frame += kwargs["data"] #TODO data length should be configured

            return frame + padding

        def _headers():
            frame = ""
            padding = ""
            if self.state == ST.RESERVED_L:
                self.setState(ST.HCLOSED_R) # suspicious
            self.setState(ST.OPEN) # here?
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
                self.setState(ST.HCLOSED_L)
            elif flag == FLAG.END_STREAM:
                self.setState(ST.HCLOSED_L)

            # continuation frame should be used if length is ~~ ?
           # should continuation frame be used from app side??
            frame += kwargs["wire"] + padding
            return frame

        def _priority():
            streamDependency = packHex(kwargs["depend"], 4)
            if kwargs.has_key("E") and kwargs["E"]:
                # TODO: must fix, not cool
                streamDependency[0] = unhexlify(hex(upackHex(streamDependency[0]) | 0x80)[2:])
            weight = packHex(kwargs["weight"], 1)
            return streamDependency + weight

        def _rst_stream():
            self.setState(ST.CLOSED)
            return packHex(kwargs["err"], 4)

        def _settings():
            if flag == FLAG.NO or flag == FLAG.ACK:
                return ""
            frame = packHex(kwargs["identifier"], 2) + packHex(kwargs["value"], 4)
            return frame

        def _push_promise():
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(kwargs["padLen"], 1)
                padding = packHex(0, kwargs["padLen"])
            elif flag == FLAG.END_HEADERS:
                pass
            # make new stream
            promisedId = packHex(kwargs["pushId"], 4)
            self.connection.addStream(kwargs["pushId"], ST.RESERVED_L)
            if kwargs.has_key("R") and kwargs["R"]:
                promisedId[0] = unhexlify(hex(upackHex(promisedId[0]) | 0x80)[2:])
            wire = unhexlify(encode(self.headers, True, True, True, self.table))
            return frame + promisedId + wire + padding

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
            if kwargs.has_key("R") and kwargs["R"]:
                windowSizeIncrement[0] = unhexlify(hex(upackHex(windowSizeIncrement[0]) | 0x80)[2:])
            return windowSizeIncrement

        def _continuation(wire):
            # enough
            return wire

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
