from binascii import hexlify
from settings import *

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

def list2dict(headers):
    # TODO: temporaly use
    # from [[":method", "GET"] ...] to {":method":"GET" ...}
    dist = {}
    for header in headers:
        dist[header.keys()[0]] = header.values()[0]
    return dist

def dict2list(headers):
    # TODO: temporaly use
    # from {":method":"GET"...} to [[":method", "GET"] ...]
    dist = []
    for k in headers:
        dist.append([k, headers[k]])
    return dist

def getSrc(path):
    try:
        with open(path) as f:
            lines = f.readlines()
    except Exception as e:
        lines = ["No such file or directory"]
    return lines

def getSrcLinks(lines):
    links = []
    for line in lines:
        if "src" in line or ("href" in line and "text/css" in line):
            if "src" in line:
                srcAfter = line.split("src=")[1]
                links.append(srcAfter[1:srcAfter[1:].find(srcAfter[0])+1])
            elif "href" in line:
                srcAfter = line.split("href=")[1]
                links.append(srcAfter[1:srcAfter[1:].find(srcAfter[0])+1])
    return links
