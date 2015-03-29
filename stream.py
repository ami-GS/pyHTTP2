import struct
from settings import *
from util import *

class Stream():
    def __init__(self, stream_id, connection, state):
        self.sId = stream_id
        self.connection = connection
        self.state = state
        self.windowSize = connection.initialWindowSize
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
