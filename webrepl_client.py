#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import struct
try:
    import usocket as socket
except ImportError:
    import socket
from . import websocket_helper

# Define to 1 to use builtin "websocket" module of MicroPython
USE_BUILTIN_WEBSOCKET = 0
# Treat this remote directory as a root for file transfers
SANDBOX = ""
#SANDBOX = "/tmp/webrepl/"
DEBUG = 0

WEBREPL_FILE = "<2sBBQLH64s"


def debugmsg(msg):
    if DEBUG:
        print(msg)


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

        def read(self, size, text_ok=False):
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
                    if text_ok and fl == 0x81:
                        break
                    debugmsg("Got unexpected websocket record of type %x, skipping it" % fl)
                    while sz:
                        skip = self.s.recv(sz)
                        debugmsg("Skip data: %s" % skip)
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


class WebREPLClient(object):
    def __init__(self, password, host='192.168.4.1', port=8266, keep_socket_connected=False):
        self.host = host
        self.port = port
        self.keep_socket_connected = keep_socket_connected
        self.password = password
        self.ws = None

    def login(self):
        while True:
            c = self.ws.read(1, text_ok=True)
            if c == b":":
                assert self.ws.read(1, text_ok=True) == b" "
                break
        self.ws.write(self.password.encode("utf-8") + b"\r")

    def connect(self):
        s = socket.socket()

        ai = socket.getaddrinfo(self.host, self.port)
        addr = ai[0][4]

        s.connect(addr)
        # s = s.makefile("rwb")
        websocket_helper.client_handshake(s)

        self.ws = websocket(s)

        self.login()

        # Set websocket to send data marked as "binary"
        self.ws.ioctl(9, 2)

    def get_file(self, local_file, remote_file):
        if self.ws is None:
            self.connect()
        src_fname = (SANDBOX + remote_file).encode("utf-8")
        rec = struct.pack(WEBREPL_FILE, b"WA", 2, 0, 0, 0, len(src_fname), src_fname)
        print(rec, len(rec))
        self.ws.write(rec)
        assert self.read_resp() == 0
        with open(local_file, "wb") as f:
            while True:
                (sz,) = struct.unpack("<H", self.ws.read(2))
                if sz == 0:
                    break
                while sz:
                    buf = self.ws.read(sz)
                    if not buf:
                        raise OSError()
                    f.write(buf)
                    sz -= len(buf)
        assert self.read_resp() == 0
        if not self.keep_socket_connected:
            self.ws.close()

    def put_file(self, local_file, remote_file):
        sz = os.stat(local_file)[6]
        dest_fname = (SANDBOX + remote_file).encode("utf-8")
        rec = struct.pack(WEBREPL_FILE, b"WA", 1, 0, 0, sz, len(dest_fname), dest_fname)
        debugmsg("%r %d" % (rec, len(rec)))
        self.ws.write(rec[:10])
        self.ws.write(rec[10:])
        assert self.read_resp() == 0
        cnt = 0
        with open(local_file, "rb") as f:
            while True:
                sys.stdout.write("Sent %d of %d bytes\r" % (cnt, sz))
                sys.stdout.flush()
                buf = f.read(1024)
                if not buf:
                    break
                self.ws.write(buf)
                cnt += len(buf)
        print()
        assert self.read_resp() == 0

    def read_resp(self):
        data = self.ws.read(4)
        sig, code = struct.unpack("<2sH", data)
        assert sig == b"WB"
        return code
