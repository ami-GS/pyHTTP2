from settings import *
from stream import Stream
import socket
from util import *
from pyHPACK import HPACK
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
        self.peerSettingACK = False
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
        frame.sendEval(self) #TODO: makeWire and send if this returns true
        state = self.getStreamState(frame.streamID)
        if frame.flags&FLAG.END_STREAM == FLAG.END_STREAM:
            if state == STATE.OPEN:
                self.setStreamState(frame.streamID, STATE.HCLOSED_L)
            elif state == STATE.HCLOSED_R:
                self.setStreamState(frame.streamID, STATE.CLOSED)
        frame.makeWire()
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
        else:
            print "WARNNING: undefined frame type"

        if flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
            stream = self.streams[streamID]
            frame.headers = HPACK.decode(stream.headerFlagment + frame.headerFlagment, self.table)
            stream.initFlagment()
        return frame

    def validateData(self):
        if self.preface:
            headerOctet = self._recv(9)
            if len(headerOctet) == 0:
                # when connection closed from client
                self.preface = False
                return False
            length, frameType, flags, streamID = Http2Header.getHeaderInfo(headerOctet)
            if not self.streams.get(streamID, ''):
                self.addStream(streamID)
            frame = self.getFrame(frameType, flags, streamID, headerOctet+self._recv(length))
            print "RECV\n\t%s" % frame.string()
            if self.streams[streamID].continuing and frameType != TYPE.CONTINUATION:
                self.sendFrame(Goaway(self.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
            frame.recvEval(self)
        else:
            data = self._recv(24)
            if data == CONNECTION_PREFACE:
                self.preface = True
        return True

    def addStream(self, ID, state = STATE.IDLE):
        self.streams[ID] = Stream(ID, self.initialWindowSize, state)

    def setHeaderTableSize(self, size):
        self.table.setMaxHeaderTableSize(size)

    def useWindow(self, ID, size):
        self.streams[0].useWindow(size)
        self.streams[ID].useWindow(size)

    def recoverWindow(self, ID, size):
        self.streams[ID].recoverWindow(size)

    def setInitialWindowSize(self, size):
        for ID in self.streams:
            if self.stream[ID].state != STATE.IDLE:
                self.stream[ID].setInitialWindowSize(size)
