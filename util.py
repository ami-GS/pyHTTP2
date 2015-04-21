from binascii import hexlify

def packHex(val, l):
    h = ""
    if type(val) == str:
        h += val[:l]
        h = "\x00"*(l-len(h)) + h
    else:
        for i in range(l-1, -1 ,-1):
            h += chr((val & (0xff << (i * 8))) >> (i * 8))
    return h

def upackHex(val):
    return int(hexlify(val), 16)

def convert2dict(headers):
    # TODO: temporaly use
    dist = {}
    for header in headers:
        dist[header.keys()[0]] = header.values()[0]
    return dist
