LIMIT_MAX_FRAME_SIZE = (1 << 24) - 1
INITIAL_MAX_FRAME_SIZE = 1 << 14
MAX_WINDOW_SIZE = (1 << 31) - 1
FRAME_HEADER_SIZE = 9

CONNECTION_PREFACE = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

class TYPE():
    DATA = 0x00
    HEADERS = 0x01
    PRIORITY = 0x02
    RST_STREAM = 0x03
    SETTINGS = 0x04
    PUSH_PROMISE = 0x05
    PING = 0x06
    GOAWAY = 0x07
    WINDOW_UPDATE = 0x08
    CONTINUATION = 0x09

    @classmethod
    def string(cls, num):
        if num == cls.DATA:
            return "DATA"
        elif num == cls.HEADERS:
            return "HEADERS"
        elif num == cls.PRIORITY:
            return "PRIORITY"
        elif num == cls.RST_STREAM:
            return "RST STREAM"
        elif num == cls.SETTINGS:
            return "SETTINGS"
        elif num == cls.PUSH_PROMISE:
            return "PUSH PROMISE"
        elif num == cls.PING:
            return "PING"
        elif num == cls.GOAWAY:
            return "GOAWAY"
        elif num == cls.WINDOW_UPDATE:
            return "WINDOW UPDATE"
        elif num == cls.CONTINUATION:
            return "CONTINUATION"
        else:
            return "WARNNING: undefined frame type"

class FLAG():
    NO = 0x00
    ACK = 0x01
    END_STREAM = 0x01
    END_HEADERS = 0x04
    PADDED = 0x08
    PRIORITY = 0x20

    @classmethod
    def string(cls, num):
        val = ""
        if num&cls.NO == cls.NO:
            val += "NO; "
        if num&cls.ack == cls.ACK:
            val += "ACK or END STREAM; "
        if num&cls.END_HEADERS == cls.END_HEADERS:
            val += "END HEADERS; "
        if num&cls.PADDED == cls.PADDED:
            val += "PADDED; "
        if num&cls.PRIORITY == cls.PRIORITY:
            val += "PRIORITY; "
        return val[:-2]
    
class SETTINGS():
    NO = 0x00
    HEADER_TABLE_SIZE = 0x01
    ENABLE_PUSH = 0x02
    MAX_CONCURRENT_STREAMS = 0x03
    INITIAL_WINDOW_SIZE = 0x04
    MAX_FRAME_SIZE = 0x05
    MAX_HEADER_LIST_SIZE = 0x06
    INIT_VALUE = {"table_size": 4096, "enable_push": 1, "concurrent_streams": -1,
                  "window_size": 65535, "frame_size": 16384, "header_list_size": -1}

    @classmethod
    def string(cls, num):
        if num == cls.NO:
            return "NO"
        elif num == cls.HEADER_TABLE_SIZE:
            return "HEADER TABLE SIZE"
        elif num == cls.ENABLE_PUSH:
            return "ENABLE PUSH"
        elif num == cls.MAX_CONCURRENT_STREAMS:
            return "MAX CONCURRENT STREAMS"
        elif num == cls.INITIAL_WINDOW_SIZE:
            return "INITIAI WINODW SIZE"
        elif num == cls.MAX_FRAME_SIZE:
            return "MAX FRAME SIZE"
        elif num == cls.MAX_HEADER_LIST_SIZE:
            return "MAX HEADER LIST SIZE"

class ERR_CODE():
    NO_ERROR = 0x00
    PROTOCOL_ERROR = 0x01
    INTERNAL_ERROR = 0x02
    FLOW_CONTROL_ERROR = 0x03
    SETTINGS_TIMEOUT = 0x04
    STREAM_CLOSED = 0x05
    FRAME_SIZE_ERROR = 0x06
    REFUSED_STREAM = 0x07
    CANCEL = 0x08
    COMPRESSION_ERROR = 0x09
    CONNECT_ERROR = 0x0a
    ENHANCE_YOUR_CALM = 0x0b
    INADEQUATE_SECURITY = 0x0c
    HTTP_1_1_REQUIRED = 0x0d

    @classmethod
    def string(cls, num):
        if num == cls.NO_ERROR:
            return "NO ERROR"
        elif num == cls.PROTOCOL_ERROR:
            return "PROTOCOL ERROR"
        elif num == cls.INTERNAL_ERROR:
            return "INTERNAL ERROR"
        elif num == cls.FLOW_CONTROL_ERROR:
            return "FLOW CONTROL ERROR"
        elif num == cls.SETTINGS_TIMEOUT:
            return "SETTINGS TIMEOUT"
        elif num == cls.STREAM_CLOSED:
            return "STREAM CLOSED"
        elif num == cls.FRAME_SIZE_ERROR:
            return "FRAME SIZE ERROR"
        elif num == cls.REFUSED_STREAM:
            return "REFUSED STREAM"
        elif num == cls.CANCEL:
            return "CANCEL"
        elif num == cls.COMPRESSION_ERROR:
            return "COMPRESSION ERROR"
        elif num == cls.CONNECT_ERROR:
            return "CONNECT ERROR"
        elif num == cls.ENHANCE_YOUR_CALM:
            return "ENHANCE YOUR CALM"
        elif num == cls.INADEQUATE_SECURITY:
            return "INADEQUATE SECURITY"
        elif num == cls.HTTP_1_1_REQUIRED:
            return "HTTP 1.1 REQUIRED"
        else:
            return "WARNING: undefined error code"

class STATE():
    IDLE = 0x00
    RESERVED_L = 0x01
    RESERVED_R = 0x02
    OPEN = 0x03
    HCLOSED_L = 0x04
    HCLOSED_R = 0x05
    CLOSED = 0x06

    @classmethod
    def string(cls, num):
        if num == cls.IDLE:
            return "idle"
        elif num == cls.RESERVED_L:
            return "reserved (local)"
        elif num == cls.RESERVED_R:
            return "reserved (remote)"
        elif num == cls.OPEN:
            return "open"
        elif num == cls.HCLOSED_L:
            return "half closed (local)"
        elif num == cls.HCLOSED_R:
            return "half closed (remote)"
        elif num == cls.CLOSED:
            return "closed"


INITIAL_STREAM_STATE = {"state":STATE.IDLE, "header":[True,""],"windowSize":65535}
