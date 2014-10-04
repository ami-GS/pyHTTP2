from pyHPACK.HPACK import encode
from settings import BaseFlag, FrameType, Settings, ErrorCode

Flag = BaseFlag()
Type = FrameType()
Set = Settings()
Err = ErrorCode()

wireWrapper = lambda x: "".join([chr(int(x[i:i+2], 16)) for i in range(0, len(x), 2)])

def packHex(val, l):
    l /= 8
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

def HTTP2Frame(length, type, flag, stream_id):
    return packHex(length, 24) + packHex(type, 8) + packHex(flag, 8) + packHex(stream_id, 32)

def HeadersFrame(flag, headers, stream_id, table, padLen = 0):
    frame = ""
    padding = ""
    if flag == Flag.PADDED:
        frame += packHex(padLen, 8) # Pad Length
        padding = packHex(0, padLen)
    elif flag == Flag.PRIORITY:
        # 'E' also should be here
        frame += packHex(0, 32) # Stream Dependency
        frame += packHex(0, 8) # Weight
    frame += wireWrapper(encode(headers, True, True, True, table)) + padding
    return HTTP2Frame(len(frame), Type.HEADERS, flag, stream_id) + frame

def SettingsFrame(flag = Flag.NO, stream_id = 0, identifier = Set.NO, value = 0):
    if flag == Flag.NO:
        return HTTP2Frame(0, Type.SETTINGS, flag, stream_id)
    frame = packHex(identifier, 16) + packHex(value, 32)
    return HTTP2Frame(48, Type.SETTINGS, flag, stream_id) + frame

def GoAwayFrame(lastStream_id, errorCode = Err.NO_ERROR, debugData = ""):
    # R also should be here
    frame = packHex(lastStream_id, 32)
    frame += packHex(errorCode, 32)
    frame += debugData if debugData else ""
    return HTTP2Frame(len(frame), Type.GOAWAY, Flag.NO, 0) + frame
