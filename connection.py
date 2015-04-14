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
        print "%s\n\t%s" % (sendC.apply("SEND"), frame.string())
        self._send(frame.getWire())

    def setStreamState(self, ID, state):
        self.streams[ID].setState(state)

    def getStreamState(self, ID):
        return self.streams[ID].getState()

    def initFlagment(self, ID):
        self.streams[ID].initFlagment()

    def appendFlagment(self, ID, flagment):
        self.streams[ID].appendFlagment(flagment)

    def getFrameFunc(self, frameType):
        if frameType == TYPE.DATA:
            return Data.getFrame
        elif frameType == TYPE.HEADERS:
            return Headers.getFrame
        elif frameType == TYPE.PRIORITY:
            return Priority.getFrame
        elif frameType == TYPE.RST_STREAM:
            return Rst_Stream.getFrame
        elif frameType == TYPE.SETTINGS:
            return Settings.getFrame
        elif frameType == TYPE.PUSH_PROMISE:
            return Push_Promise.getFrame
        elif frameType == TYPE.PING:
            return Ping.getFrame
        elif frameType == TYPE.GOAWAY:
            return Goaway.getFrame
        elif frameType == TYPE.WINDOW_UPDATE:
            return Window_Update.getFrame
        elif frameType == TYPE.CONTINUATION:
            return Continuation.getFrame
        else:
            print "WARNNING: undefined frame type"
            return #raise

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
            frameFunc = self.getFrameFunc(frameType)
            frame = frameFunc(flags, streamID, headerOctet+self._recv(length))
            stream = self.streams[streamID]
            if flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
                frame.headers = HPACK.decode(
                    stream.headerFlagment+frame.headerFlagment, self.table)
                stream.initFlagment()
            print "%s\n\t%s" % (recvC.apply("RECV"), frame.string())
            if stream.continuing and frameType != TYPE.CONTINUATION:
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
