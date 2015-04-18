from settings import *
from stream import Stream
import socket
from util import *
from pyHPACK import HPACK
from pyHPACK.tables import Table
from frame import *

class Connection(object):
    def __init__(self, sock, addr, enable_tls, debug, is_client = False):
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
        self.preface = is_client
        self.is_goaway = False
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
        if frame.flags&FLAG.END_STREAM == FLAG.END_STREAM:
            stream = self.streams.get(frame.streamID, None)
            state = stream.getState()
            if state == STATE.OPEN:
                stream.setState(STATE.HCLOSED_L)
            elif state == STATE.HCLOSED_R:
                stream.setState(STATE.CLOSED)
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

    def validateData(self):
        if self.preface:
            headerOctet = self._recv(9)
            if len(headerOctet) == 0:
                # when connection closed from client
                self.preface = False
                return False
            info = Http2Header.getHeaderInfo(headerOctet)
            if not self.is_goaway or self.is_goaway and (info.type == TYPE.HEADERS or
                                                         info.type == TYPE.PRIORITY or
                                                         info.type == TYPE.CONTINUATION):
                stream = self.streams.get(info.streamID, '')
                if not stream:
                    self.addStream(info.streamID)
                    stream = self.streams[info.streamID]
                if (stream.getState() == STATE.CLOSED and
                    info.type != TYPE.PRIORITY and
                    info.type != TYPE.RST_STREAM):
                    self.sendFrame(Rst_Stream(info.streamID, err=ERR_CODE.STREAM_CLOSED))
                frameFunc = getFrameFunc(info.type)
                frame = frameFunc(info, self._recv(info.length))
                if info.flags&FLAG.END_HEADERS == FLAG.END_HEADERS:
                    frame.headers = HPACK.decode(
                        stream.headerFlagment+frame.headerFlagment, self.table)
                    stream.initFlagment()
                print "%s\n\t%s" % (recvC.apply("RECV"), frame.string())
                if stream.continuing and info.type != TYPE.CONTINUATION:
                    self.sendFrame(Goaway(self.lastStreamID, err=ERR_CODE.PROTOCOL_ERROR))
                frame.recvEval(self)
            else:
                self._recv(info.length)
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
