class Stream():
    def __init__(self, streamID, windowSize, state, weight=16):
        self.ID = streamID
        self.state = state
        self.weight = weight
        self.initialWindowSize = windowSize
        self.windowSize = windowSize
        self.headerFlagment = ""
        self.continuing = False
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

    def initFlagment(self):
        self.headerFlagment = ""
        self.continuing = False

    def appendFlagment(self, flagment):
        self.headerflagment += flagment
        self.continuing = True

    def setParentStream(self, E, pStream):
        if E:
            for cStream in stream.dependencyTree["children"]:
                cStream.setParentStream(0, self)
                self.setChildStream(cStream)
            pStream.dependencyTree["children"] = []
        self.dependencyTree["parent"] = pstream
        pStream.setChildStream(self)

    def setChildStream(self, cStream):
        self.dependencyTree["children"].append(cStream)

    def setWeight(self, weight):
        self.weight = weight
