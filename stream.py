from settings import *

class Stream():
    def __init__(self, streamID, windowSize, state, weight=16):
        self.ID = streamID
        self.state = state
        self.weight = weight
        self.initialWindowSize = windowSize
        self.windowSize = windowSize
        self.headers = {}
        self.headerFlagment = ""
        self.continuing = False
        self.finRequest = {} # {"samole.css":"GET", "sample.css":"GET"}
        self.dependencyTree = {"parent":None, "children":[]}

    def recoverWindow(self, size):
        self.windowSize += size

    def useWindow(self, size):
        self.windowSize -= size

    def setInitialWindowSize(self, size):
        self.initialWindowSize = size
        self.windowSize = size - (self.initialWindowSize - self.windowSize)

    def getState(self):
        return self.state

    def setState(self, state):
        self.state = state

    def getUrl(self, path = ""):
        if not path:
            path = self.headers[":path"]
        if not path.startswith("/"):
            path = "/" + path
        return self.headers[":scheme"] + "://" + self.headers[":authority"] + path

    def initFlagment(self):
        self.headerFlagment = ""
        self.continuing = False

    def appendFlagment(self, flagment):
        self.headerflagment += flagment
        self.continuing = True

    def setParentStream(self, E, pStream):
        if E:
            for cStream in pStream.dependencyTree["children"]:
                cStream.setParentStream(0, self)
            pStream.dependencyTree["children"] = []
        self.dependencyTree["parent"] = pStream
        pStream.setChildStream(self)

    def setChildStream(self, cStream):
        self.dependencyTree["children"].append(cStream)

    def setWeight(self, weight):
        self.weight = weight

    def setHeaders(self, headers):
        self.headers = headers

    def sendEval(self, flags):
        if flags&FLAG.END_STREAM == FLAG.END_STREAM:
            if self.state == STATE.OPEN:
                self.setState(STATE.HCLOSED_L)
            elif self.state == STATE.HCLOSED_R:
                self.setState(STATE.CLOSED)

    def string(self):
        return "%s: streamID=%d, state=%s, rest window=%d headers=%s" % \
            (streamC.apply("Stream"), self.ID, STATE.string(self.state), self.windowSize, self.headers)
