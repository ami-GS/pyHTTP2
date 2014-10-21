from binascii import hexlify

def packHex(val, l):
    h = val if type(val) == str else chr(val)
    return "\x00"*(l-len(h)) + h

def upackHex(val):
    return int(hexlify(val), 16)
