#!/usr/bin/env python
import sys
import os
import struct
try:
    import usocket as socket
except ImportError:
    import socket
import websocket_helper

# Define to 1 to use builtin "websocket" module of MicroPython
USE_BUILTIN_WEBSOCKET = 0
# Treat this remote directory as a root for file transfers
SANDBOX = "."
#SANDBOX = "/tmp/webrepl/"


WEBREPL_FILE = "<3sBBBHQH64s"

if USE_BUILTIN_WEBSOCKET:
    from websocket import websocket
else:
    class websocket:

        def __init__(self, s):
            self.s = s
            self.buf = b""

        def write(self, data):
            l = len(data)
            if l < 126:
                # TODO: hardcoded "binary" type
                hdr = struct.pack(">BB", 0x82, l)
            else:
                hdr = struct.pack(">BBH", 0x82, 126, l)
            self.s.send(hdr)
            self.s.send(data)

        def recvexactly(self, sz):
            res = b""
            while sz:
                data = self.s.recv(sz)
                if not data:
                    break
                res += data
                sz -= len(data)
            return res

        def read(self, size):
            if not self.buf:
                while True:
                    hdr = self.recvexactly(2)
                    assert len(hdr) == 2
                    fl, sz = struct.unpack(">BB", hdr)
                    if sz == 126:
                        hdr = self.recvexactly(2)
                        assert len(hdr) == 2
                        (sz,) = struct.unpack(">H", hdr)
                    if fl == 0x82:
                        break
                    print("Got unexpected websocket record of type %x, skipping it" % fl)
                    while sz:
                        skip = self.s.recv(sz)
                        print("Skip data:", skip)
                        sz -= len(skip)
                data = self.recvexactly(sz)
                assert len(data) == sz
                self.buf = data

            d = self.buf[:size]
            self.buf = self.buf[size:]
            assert len(d) == size, len(d)
            return d

        def ioctl(self, req, val):
            assert req == 9 and val == 2


def read_resp(ws):
    data = ws.read(4)
    sig, code = struct.unpack("<2sH", data)
    assert sig == b"WB"
    return code

def put_file(ws, local_file, remote_file):
    sz = os.stat(local_file)[6]
    dest_fname = bytes(SANDBOX + remote_file, "utf-8")
    rec = struct.pack(WEBREPL_FILE, b"WRA", 1, 0, 0, sz, 0, len(dest_fname), dest_fname)
    print(rec, len(rec))
    ws.write(rec[:10])
    ws.write(rec[10:])
    assert read_resp(ws) == 0
    with open(local_file, "rb") as f:
        while True:
            buf = f.read(256)
            if not buf:
                break
            ws.write(buf)
    assert read_resp(ws) == 0

def get_file(ws, local_file, remote_file):
    src_fname = bytes(SANDBOX + remote_file, "utf-8")
    rec = struct.pack(WEBREPL_FILE, b"WRA", 2, 0, 0, 0, 0, len(src_fname), src_fname)
    print(rec, len(rec))
    ws.write(rec)
    assert read_resp(ws) == 0
    with open(local_file, "wb") as f:
        while True:
            (sz,) = struct.unpack("<H", ws.read(2))
            if sz == 0:
                break
            while sz:
                buf = ws.read(sz)
                if not buf:
                    raise OSError()
                f.write(buf)
                sz -= len(buf)
    assert read_resp(ws) == 0


def help(rc=0):
    exename = sys.argv[0].rsplit("/", 1)[-1]
    print("%s - Perform remote file operations using MicroPython WebREPL protocol" % exename)
    print("Arguments:")
    print("  <host>:<remote_file> <local_file> - Copy remote file to local file")
    print("  <local_file> <host>:<remote_file> - Copy local file to remote file")
    print("Examples:")
    print("  %s script.py 192.168.4.1:/another_name.py" % exename)
    print("  %s script.py 192.168.4.1:/app/" % exename)
    print("  %s 192.168.4.1:/app/script.py ." % exename)
    sys.exit(rc)

def error(msg):
    print(msg)
    sys.exit(1)

def parse_remote(remote):
    host, fname = remote.rsplit(":", 1)
    port = 8266
    if ":" in host:
        host, port = remote.split(":")
        port = int(port)
    return (host, port, fname)

def main():

    if len(sys.argv) != 3:
        help(1)

    if ":" in sys.argv[1] and ":" in sys.argv[2]:
        error("Operations on 2 remote files are not supported")
    if ":" not in sys.argv[1] and ":" not in sys.argv[2]:
        error("One remote file is required")

    if ":" in sys.argv[1]:
        op = "get"
        host, port, src_file = parse_remote(sys.argv[1])
        dst_file = sys.argv[2]
        if os.path.isdir(dst_file):
            basename = src_file.rsplit("/", 1)[-1]
            dst_file += "/" + basename
    else:
        op = "put"
        host, port, dst_file = parse_remote(sys.argv[2])
        src_file = sys.argv[1]
        if dst_file[-1] == "/":
            basename = src_file.rsplit("/", 1)[-1]
            dst_file += basename

    if 1:
        print(op, host, port)
        print(src_file, "->", dst_file)

    s = socket.socket()

    ai = socket.getaddrinfo(host, port)
    addr = ai[0][4]

    s.connect(addr)
    #s = s.makefile("rwb")
    websocket_helper.client_handshake(s)

    ws = websocket(s)
    # Set websocket to send data marked as "binary"
    ws.ioctl(9, 2)

    if op == "get":
        get_file(ws, dst_file, src_file)
    elif op == "put":
        put_file(ws, src_file, dst_file)

    s.close()


if __name__ == "__main__":
    main()
