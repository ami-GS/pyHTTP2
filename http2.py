from pyHPACK.HPACK import encode
from settings import *
import socket

FLAG = BaseFlag
TYPE = FrameType
SET = Settings
ERR = ErrorCode

wireWrapper = lambda x: "".join([chr(int(x[i:i+2], 16)) for i in range(0, len(x), 2)])

def packHex(val, l):
    l /= 8
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

class HTTP2Base(object):
    def __init__(self, host, port, table = None):
        self.table = table
        self.host, self.port = host, port
        self.padLen = 0
        self.lastStream_id = None
        self.streams = [0]

    def send(self, frame):
        self.sock.send(frame)

    def parseData(self, data):
        def parseFrameHeader(data):
            self.readyToPayload = True
            return data[:3], data[3:4], data[4:5], data[5:9]

        def _data():
            pass
        def _headers():
            pass
        def _priority():
            pass
        def _rst_stream():
            pass
        def _settings():
            pass
        def _ping():
            pass
        def _goAway():
            pass
        def _window_update():
            pass
        def _continuation():
            pass

        Length, Type, Flags, Stream_id = 0, 0, 0, 0 #here?
        while len(data):
            if data.startswith(CONNECTION_PREFACE):
                #send settings (this may be empty)
                data = data.lstrip(CONNECTION_PREFACE)
            else:
                if self.readyToPayload:
                    self.readyToPayload = False
                    if Type == TYPE.DATA:
                        frame = _data()
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
                        print("err")
                else:
                    Length, Type, Flags, Stream_id = _parseFrameHeader(data)
                    data = data[FRAME_HEADER_SIZE:]

    def makeFrame(self, Type, flag=FLAG.NO, stream_id=0, **kwargs):
        def _HTTP2Frame(length, Type, flag, stream_id):
            return packHex(length, 24) + packHex(Type, 8) + packHex(flag, 8) + packHex(stream_id, 32)

        def _data():
            return ""

        def _headers(flag):
            frame = ""
            padding = ""
            if flag == FLAG.PADDED:
                frame += packHex(self.padLen, 8) # Pad Length
                padding = packHex(0, self.padLen)
            elif flag == FLAG.PRIORITY:
                # 'E' also should be here
                frame += packHex(0, 32) # Stream Dependency
                frame += packHex(0, 8) # Weight
            wire = wireWrapper(encode(self.headers, True, True, True, self.table))
            # continuation frame should be used if length is ~~ ?
            frame += wire + padding
            return frame

        def _priority():
            return ""

        def _rst_stream():
            return ""

        def _settings(flag, identifier = SET.NO, value = 0):
            if flag == FLAG.NO:
                return ""
            frame = packHex(identifier, 16) + packHex(value, 32)
            return frame

        def _push_promise():
            return ""

        def _ping(value):
            return packHex(value, 64)

        def _goAway(err, debug):
            # R also should be here
            frame = packHex(self.lastStream_id, 32)
            frame += packHex(err, 32)
            frame += debug if debug else ""
            return frame

        def _window_update():
            return ""

        def _continuation(wire):
            # TODO wire length and fin flag should be specified
            return wire

        # here should use **kwargs
        if Type == TYPE.DATA:
            frame = _data()
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
            print("err")
        http2Frame = _HTTP2Frame(len(frame), Type, flag, stream_id)
        return http2Frame + frame

    def addStream(self):
        self.lastStream_id += 2
        self.streams.append(self.lastStream_id)

    def setTable(self, table):
        self.table = table

    def setHeaders(self, headers):
        self.headers = headers

class Server(HTTP2Base):
    def __init__(self, host, port, table = None):    
        super(Server, self).__init__(host, port, table)
        self.sock = socket.socket(socket.AP_INET, socket.SOCK_STREAM)
        self.lastStream_id = 2
        self.streams.append(self.lastStream_id)
        self.readyToPayload = False

    def runServer(self):
        self.sock.bind((host, port))
        self.sock.listen(1) # number ?
        self.conn, self.addr = s.accept()
        while True:
            data = conn.recv((MAX_FRAME_SIZE + FRAME_HEADER_SIZE) * 8) # here should use window length ?
            print data
            reponse = "?"
            conn.send(response)

class Client(HTTP2Base):
    def __init__(self, host, port, table = None):
        super(Client, self).__init__(host, port, table)
        self.lastStream_id = 1
        self.streams.append(self.lastStream_id)
        self.sock = socket.create_connection((host, port), 5)
