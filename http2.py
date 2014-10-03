def packHex(val, l):
    l /= 8
    result = chr(val)    
    return "".join([chr(0) for _ in range(l-len(result))]) + result

def HTTP2Frame(length, type, flag, stream_id):
    return packHex(length, 24) + packHex(type, 8) + packHex(flag, 8) + packHex(stream_id, 32)
