from settings import Settings

class Stream():
    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.state = "idle"
        self.windowSize = Settings.INIT_VALUE[4]
        self.Wire = ""
        self.finWire = True

    def setWindowSize(self, windowSize):
        self.windowSize = windowSize

    def setState(self, state):
        self.state = state

    def appendWire(self, wire):
        self.wire += wire

    def getWire(self):
        return self.wire
