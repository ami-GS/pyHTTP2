LIMIT_MAX_FRAME_SIZE = (1 << 24) - 1
INITIAL_MAX_FRAME_SIZE = 1 << 14
MAX_WINDOW_SIZE = (1 << 31) - 1
FRAME_HEADER_SIZE = 9

CONNECTION_PREFACE = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

class FrameType():
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

class BaseFlag():
    NO = "\x00"
    ACK = "\x01"
    END_STREAM = "\x01"
    END_HEADERS = "\x04"
    PADDED = "\x08"
    PRIORITY = "\x20"
    
class Settings():
    NO = "\x00"
    HEADER_TABLE_SIZE = "\x01"
    ENABLE_PUSH = "\x02"
    MAX_CONCURRENT_STREAMS = "\x03"
    INITIAL_WINDOW_SIZE = "\x04"
    MAX_FRAME_SIZE = "\x05"
    MAX_HEADER_LIST_SIZE = "\x06"
    INIT_VALUE = [None, 4096, 1, -1, 65535, 65536, -1]

class ErrorCode():
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

class State():
    IDLE = "\x00"
    RESERVED_L = "\x01"
    RESERVED_R = "\x02"
    OPEN = "\x03"
    HCLOSED_L = "\x04"
    HCLOSED_R = "\x05"
    CLOSED = "\x06"

INITIAL_STREAM_STATE = {"state":State.IDLE, "header":[True,""],"windowSize":65535}
