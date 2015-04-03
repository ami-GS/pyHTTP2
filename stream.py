class Stream():
    def __init__(self, streamID, windowSize, state):
        self.ID = streamID
        self.state = state
        self.initialWindowSize = windowSize
        self.windowSize = windowSize
        self.headerFlagment = ""
        self.continuing = False

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
