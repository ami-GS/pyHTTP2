from pyHPACK.HPACK import encode
from settings import BaseFlag, FrameType, Settings, ErrorCode
import socket

Flag = BaseFlag
Type = FrameType
Set = Settings
Err = ErrorCode

wireWrapper = lambda x: "".join([chr(int(x[i:i+2], 16)) for i in range(0, len(x), 2)])

def packHex(val, l):
    l /= 8
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

class Connection():
    def __init__(self, host, port, hostType = "client", table = None):
        self.sock = socket.create_connection((host, port), 5)
        self.table = table
        self.padLen = 0
        self.hostType = hostType
        self.lastStream_id = 1 if hostType == "client" else 2 # here dangerous
        self.streams = [0, self.lastStream_id]

    def addStream(self):
        self.lastStream_id = self.streams[-1] + 2
        self.streams.append(self.lastStream_id)

    def send(self, frame):
        self.sock.send(frame)

    #def makeFrame(self, type, flag, stream_id, err = Err.NO_ERROR, debug = None):
    def makeFrame(self, type, flag=Flag.NO, stream_id=0, **kwargs):
        # here should use **kwargs
        if type == Type.DATA:
            frame = self._data()
        elif type == Type.HEADERS:
            frame = self._headers(flag)
        elif type == Type.PRIORITY:
            frame = self._priority()
        elif type == Type.RST_STREAM:
            frame = self._rst_stream()
        elif type == Type.SETTINGS:
            frame = self._settings(flag, kwargs["ident"], kwargs["value"])
        elif type == Type.PING:
            frame = self._ping(kwargs["ping"])
        elif type == Type.GOAWAY:
            frame = self._goAway(kwargs["err"], kwargs["debug"])
        elif type == Type.WINDOW_UPDATE:
            frame = self._window_update()
        elif type == Type.CONTINUATION:
            frame = self._continuation()
        else:
            print("err")
        http2Frame = self.HTTP2Frame(len(frame), type, flag, stream_id)
        return http2Frame + frame

    def HTTP2Frame(self, length, type, flag, stream_id):
        return packHex(length, 24) + packHex(type, 8) + packHex(flag, 8) + packHex(stream_id, 32)

    def _data(self):
        return ""

    def _headers(self, flag):
        frame = ""
        padding = ""
        if flag == Flag.PADDED:
            frame += packHex(self.padLen, 8) # Pad Length
            padding = packHex(0, self.padLen)
        elif flag == Flag.PRIORITY:
            # 'E' also should be here
            frame += packHex(0, 32) # Stream Dependency
            frame += packHex(0, 8) # Weight
        wire = wireWrapper(encode(self.headers, True, True, True, self.table))
        # continuation frame should be used if length is ~~ ?
        frame += wire + padding
        return frame

    def _priority(self):
        return ""

    def _rst_stream(self):
        return ""

    def _settings(self, flag, identifier = Set.NO, value = 0):
        if flag == Flag.NO:
            return ""
        frame = packHex(identifier, 16) + packHex(value, 32)
        return frame

    def _push_promise(self):
        return ""

    def _ping(self, value):
        return packHex(value, 64)

    def _goAway(self, err, debug):
        # R also should be here
        frame = packHex(self.lastStream_id, 32)
        frame += packHex(err, 32)
        frame += debug if debug else ""
        return frame

    def _window_update(self):
        return ""

    def _continuation(self, wire):
        # TODO wire length and fin flag should be specified
        return wire

    def setTable(self, table):
        self.table = table

    def setHeaders(self, headers):
        self.headers = headers
