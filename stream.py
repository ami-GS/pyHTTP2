class Stream():
    def __init__(self, streamID, windowSize, state):
        self.ID = streamID
        self.state = state
        self.windowSize = windowSize
        self.headerFlagment = ""
        self.continuing = False

    def setWindowSize(self, windowSize):
        self.windowSize = windowSize

    def decreaseWindow(self, size):
        self.windowSize -= size

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
