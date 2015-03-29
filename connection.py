from settings import *
from stream import Stream
import socket
import struct
from util import *
from pyHPACK.HPACK import decode
from pyHPACK.tables import Table
from frame import *

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
        self.lastStreamID = 0
        self.addStream(0)
        self.preface = False
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
        while len(self.streams[streamId].getWire()):
            if len(self.streams[streamId].getWire()) > self.wireLenLimit:
                frame = self.streams[streamId].makeFrame(TYPE.CONTINUATION, FLAG.NO)
            else:
                frame = self.streams[streamId].makeFrame(TYPE.CONTINUATION, FLAG.END_HEADERS)
            self._send(frame)

    def sendFrame(self, frame):
        print "SEND\n\t%s" % frame.string()
        self._send(frame.getWire())

    def setStreamState(self, ID, state):
        self.streams[ID].setState(state)

    def getStreamState(self, ID):
        return self.streams[ID].getState()

    def initFlagment(self, ID):
        self.streams[ID].initFlagment()

    def appendFlagment(self, ID, flagment):
        self.streams[ID].appendFlagment(flagment)

    def getFrame(self, frameType, flags, streamID, data):

        if frameType == TYPE.DATA:
            frame = Data.getFrame(flags, streamID, data)
        elif frameType == TYPE.HEADERS:
            frame = Headers.getFrame(flags, streamID, data)
        elif frameType == TYPE.PRIORITY:
            frame = Priority.getFrame(flags, streamID, data)
        elif frameType == TYPE.RST_STREAM:
            frame = Rst_Stream.getFrame(flags, streamID, data)
        elif frameType == TYPE.SETTINGS:
            frame = Settings.getFrame(flags, streamID, data)
        elif frameType == TYPE.PUSH_PROMISE:
            frame = Push_Promise.getFrame(flags, streamID, data)
        elif frameType == TYPE.PING:
            frame = Ping.getFrame(flags, streamID, data)
        elif frameType == TYPE.GOAWAY:
            frame = Goaway.getFrame(flags, streamID, data)
        elif frameType == TYPE.WINDOW_UPDATE:
            frame = Window_Update.getFrame(flags, streamID, data)
        elif frameType == TYPE.CONTINUATION:
            frame = Continuation.getFrame(flags, streamID, data)

        if flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            stream = self.streams[streamID]
            frame.headers = decode(stream.headerFlagment + frame.headerFlagment, self.table)
            stream.initFlagment()

        return frame

    def validateData(self, data):
        if data.startswith(CONNECTION_PREFACE):
            self.preface = True
            data = data.lstrip(CONNECTION_PREFACE)
        if self.preface:
            while data:
                length, frameType, flags, streamID = Http2Header.getHeaderInfo(data[:9])
                if not self.streams.has_key(streamID):
                    self.addStream(streamID)
                frame = self.getFrame(frameType, flags, streamID, data[:9+length])
                data = data[9+length:]
                print "RECV\n\t%s" % frame.string()

                if self.streams[streamID].continuing and frameType != TYPE.CONTINUATION:
                    self.sendFrame(Goaway(self.lastStreamID, ERR_CODE.PROTOCOL_ERROR))
                    continue
                frame.validate(self)

    def addStream(self, stream, state = STATE.IDLE):
        self.streams[stream] = Stream(stream, self, state)

    def setHeaderTableSize(self, size):
        self.table.setMaxHeaderTableSize(size)
