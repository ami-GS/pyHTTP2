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

    @classmethod
    def string(cls, num):
        # 4 octet comes
        if num[:3] == "\x00\x00\x00":
            if num[-1] == cls.NO_ERROR:
                return "NO ERROR"
            elif num[-1] == cls.PROTOCOL_ERROR:
                return "PROTOCOL ERROR"
            elif num[-1] == cls.INTERNAL_ERROR:
                return "INTERNAL ERROR"
            elif num[-1] == cls.FLOW_CONTROL_ERROR:
                return "FLOW CONTROL ERROR"
            elif num[-1] == cls.SETTINGS_TIMEOUT:
                return "SETTINGS TIMEOUT"
            elif num[-1] == cls.STREAM_CLOSED:
                return "STREAM CLOSED"
            elif num[-1] == cls.FRAME_SIZE_ERROR:
                return "FRAME SIZE ERROR"
            elif num[-1] == cls.REFUSED_STREAM:
                return "REFUSED STREAM"
            elif num[-1] == cls.CANCEL:
                return "CANCEL"
            elif num[-1] == cls.COMPRESSION_ERROR:
                return "COMPRESSION ERROR"
            elif num[-1] == cls.CONNECT_ERROR:
                return "CONNECT ERROR"
            elif num[-1] == cls.ENHANCE_YOUR_CALM:
                return "ENHANCE YOUR CALM"
            elif num[-1] == cls.INADEQUATE_SECURITY:
                return "INADEQUATE SECURITY"
            elif num[-1] == cls.HTTP_1_1_REQUIRED:
                return "HTTP 1.1 REQUIRED"
            else:
                return "WARNING: undefined eror code"
        else:
            return "WARNING: undefined error code"

class STATE():
    IDLE = "\x00"
    RESERVED_L = "\x01"
    RESERVED_R = "\x02"
    OPEN = "\x03"
    HCLOSED_L = "\x04"
    HCLOSED_R = "\x05"
    CLOSED = "\x06"

INITIAL_STREAM_STATE = {"state":STATE.IDLE, "header":[True,""],"windowSize":65535}
