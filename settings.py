LIMIT_MAX_FRAME_SIZE = (1 << 24) - 1
INITIAL_MAX_FRAME_SIZE = 1 << 14
MAX_WINDOW_SIZE = (1 << 31) - 1
FRAME_HEADER_SIZE = 9

CONNECTION_PREFACE = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

class TYPE():
    DATA = "\x00"
    HEADERS = "\x01"
    PRIORITY = "\x02"
    RST_STREAM = "\x03"
    SETTINGS = "\x04"
    PUSH_PROMISE = "\x05"
    PING = "\x06"
    GOAWAY = "\x07"
    WINDOW_UPDATE = "\x08"
    CONTINUATION = "\x09"

    @classmethod
    def string(cls, num):
        if num == cls.DATA:
            return "DATA"
        if num == cls.HEADERS:
            return "HEADERS"
        if num == cls.PRIORITY:
            return "PRIORITY"
        if num == cls.RST_STREAM:
            return "RST STREAM"
        if num == cls.SETTINGS:
            return "SETTINGS"
        if num == cls.PUSH_PROMISE:
            return "PUSH PROMISE"
        if num == cls.PING:
            return "PING"
        if num == cls.GOAWAY:
            return "GOAWAY"
        if num == cls.WINDOW_UPDATE:
            return "WINDOW UPDATE"
        if num == cls.CONTINUATION:
            return "CONTINUATION"

class FLAG():
    NO = "\x00"
    ACK = "\x01"
    END_STREAM = "\x01"
    END_HEADERS = "\x04"
    PADDED = "\x08"
    PRIORITY = "\x20"

    @classmethod
    def string(cls, num):
        if num == cls.NO:
            return "NO"
        if num == cls.ACK:
            return "ACK or END STREAM"
        if num == cls.END_HEADERS:
            return "END HEADERS"
        if num == cls.PADDED:
            return "PADDED"
        if num == cls.PRIORITY:
            return "PRIORITY"
    
class SETTINGS():
    NO = "\x00"
    HEADER_TABLE_SIZE = "\x01"
    ENABLE_PUSH = "\x02"
    MAX_CONCURRENT_STREAMS = "\x03"
    INITIAL_WINDOW_SIZE = "\x04"
    MAX_FRAME_SIZE = "\x05"
    MAX_HEADER_LIST_SIZE = "\x06"
    INIT_VALUE = {"table_size": 4096, "enable_push": 1, "concurrent_streams": -1,
                  "window_size": 65535, "frame_size": 16384, "header_list_size": -1}

class ERR_CODE():
    NO_ERROR = "\x00"
    PROTOCOL_ERROR = "\x01"
    INTERNAL_ERROR = "\x02"
    FLOW_CONTROL_ERROR = "\x03"
    SETTINGS_TIMEOUT = "\x04"
    STREAM_CLOSED = "\x05"
    FRAME_SIZE_ERROR = "\x06"
    REFUSED_STREAM = "\x07"
    CANCEL = "\x08"
    COMPRESSION_ERROR = "\x09"
    CONNECT_ERROR = "\x0a"
    ENHANCE_YOUR_CALM = "\x0b"
    INADEQUATE_SECURITY = "\x0c"
    HTTP_1_1_REQUIRED = "\x0d"

    @staticmethod
    def string(num):
        if num == 0:
            return "NO ERROR"
        elif num == 1:
            return "PROTOCOL ERROR"
        elif num == 2:
            return "INTERNAL ERROR"
        elif num == 3:
            return "FLOW CONTROL ERROR"
        elif num == 4:
            return "SETTINGS TIMEOUT"
        elif num == 5:
            return "STREAM CLOSED"
        elif num == 6:
            return "FRAME SIZE ERROR"
        elif num == 7:
            return "REFUSED STREAM"
        elif num == 8:
            return "CANCEL"
        elif num == 9:
            return "COMPRESSION ERROR"
        elif num == 10:
            return "CONNECT ERROR"
        elif num == 11:
            return "ENHANCE YOUR CALM"
        elif num == 12:
            return "INADEQUATE SECURITY"
        elif num == 13:
            return "HTTP 1.1 REQUIRED"
        else:
            return "WARNING: undefined eror code"

class STATE():
    IDLE = "\x00"
    RESERVED_L = "\x01"
    RESERVED_R = "\x02"
    OPEN = "\x03"
    HCLOSED_L = "\x04"
    HCLOSED_R = "\x05"
    CLOSED = "\x06"

INITIAL_STREAM_STATE = {"state":STATE.IDLE, "header":[True,""],"windowSize":65535}
