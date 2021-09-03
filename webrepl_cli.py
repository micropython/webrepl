#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import struct
try:
    import usocket as socket
except ImportError:
    import socket

# Define to 1 to use builtin "uwebsocket" module of MicroPython
USE_BUILTIN_UWEBSOCKET = 0
# Treat this remote directory as a root for file transfers
SANDBOX = ""
#SANDBOX = "/tmp/webrepl/"
DEBUG = 0

WEBREPL_REQ_S = "<2sBBQLH64s"
WEBREPL_PUT_FILE = 1
WEBREPL_GET_FILE = 2
WEBREPL_GET_VER  = 3
WEBREPL_FRAME_TXT = 0x81
WEBREPL_FRAME_BIN = 0x82


def debugmsg(msg):
    if DEBUG:
        print(msg)


if USE_BUILTIN_UWEBSOCKET:
    from uwebsocket import websocket
else:
    class websocket:

        def __init__(self, s):
            self.s = s
            self.buf = b""

        def write(self, data, frame=WEBREPL_FRAME_BIN):
            l = len(data)
            if l < 126:
                hdr = struct.pack(">BB", frame, l)
            else:
                hdr = struct.pack(">BBH", frame, 126, l)
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


def login(ws, passwd):
    while True:
        c = ws.read(1, text_ok=True)
        if c == b":":
            assert ws.read(1, text_ok=True) == b" "
            break
    ws.write(passwd.encode("utf-8") + b"\r")

def read_resp(ws):
    data = ws.read(4)
    sig, code = struct.unpack("<2sH", data)
    assert sig == b"WB"
    return code


def send_req(ws, op, sz=0, fname=b""):
    rec = struct.pack(WEBREPL_REQ_S, b"WA", op, 0, 0, sz, len(fname), fname)
    debugmsg("%r %d" % (rec, len(rec)))
    ws.write(rec)


def get_ver(ws):
    send_req(ws, WEBREPL_GET_VER)
    d = ws.read(3)
    d = struct.unpack("<BBB", d)
    return d


def do_repl(ws):
    import termios, select

    class ConsolePosix:
        def __init__(self):
            self.infd = sys.stdin.fileno()
            self.infile = sys.stdin.buffer.raw
            self.outfile = sys.stdout.buffer.raw
            self.orig_attr = termios.tcgetattr(self.infd)

        def enter(self):
            # attr is: [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
            attr = termios.tcgetattr(self.infd)
            attr[0] &= ~(
                termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON
            )
            attr[1] = 0
            attr[2] = attr[2] & ~(termios.CSIZE | termios.PARENB) | termios.CS8
            attr[3] = 0
            attr[6][termios.VMIN] = 1
            attr[6][termios.VTIME] = 0
            termios.tcsetattr(self.infd, termios.TCSANOW, attr)

        def exit(self):
            termios.tcsetattr(self.infd, termios.TCSANOW, self.orig_attr)

        def readchar(self):
            res = select.select([self.infd], [], [], 0)
            if res[0]:
                return self.infile.read(1)
            else:
                return None

        def write(self, buf):
            self.outfile.write(buf)

    print("Use Ctrl-] to exit this shell")
    console = ConsolePosix()
    console.enter()
    try:
        while True:
            sel = select.select([console.infd, ws.s], [], [])
            c = console.readchar()
            if c:
                if c == b"\x1d":  # ctrl-], exit
                    break
                else:
                    ws.write(c, WEBREPL_FRAME_TXT)
            if ws.s in sel[0]:
                c = ws.read(1, text_ok=True)
                while c is not None:
                    # pass character through to the console
                    oc = ord(c)
                    if oc in (8, 9, 10, 13, 27) or oc >= 32:
                        console.write(c)
                    else:
                        console.write(b"[%02x]" % ord(c))
                    if ws.buf:
                        c = ws.read(1)
                    else:
                        c = None
    finally:
        console.exit()


def put_file(ws, local_file, remote_file):
    sz = os.stat(local_file)[6]
    dest_fname = (SANDBOX + remote_file).encode("utf-8")
    rec = struct.pack(WEBREPL_REQ_S, b"WA", WEBREPL_PUT_FILE, 0, 0, sz, len(dest_fname), dest_fname)
    debugmsg("%r %d" % (rec, len(rec)))
    ws.write(rec[:10])
    ws.write(rec[10:])
    assert read_resp(ws) == 0
    cnt = 0
    with open(local_file, "rb") as f:
        while True:
            sys.stdout.write("Sent %d of %d bytes\r" % (cnt, sz))
            sys.stdout.flush()
            buf = f.read(1024)
            if not buf:
                break
            ws.write(buf)
            cnt += len(buf)
    print()
    assert read_resp(ws) == 0

def get_file(ws, local_file, remote_file):
    src_fname = (SANDBOX + remote_file).encode("utf-8")
    rec = struct.pack(WEBREPL_REQ_S, b"WA", WEBREPL_GET_FILE, 0, 0, 0, len(src_fname), src_fname)
    debugmsg("%r %d" % (rec, len(rec)))
    ws.write(rec)
    assert read_resp(ws) == 0
    with open(local_file, "wb") as f:
        cnt = 0
        while True:
            ws.write(b"\0")
            (sz,) = struct.unpack("<H", ws.read(2))
            if sz == 0:
                break
            while sz:
                buf = ws.read(sz)
                if not buf:
                    raise OSError()
                cnt += len(buf)
                f.write(buf)
                sz -= len(buf)
                sys.stdout.write("Received %d bytes\r" % cnt)
                sys.stdout.flush()
    print()
    assert read_resp(ws) == 0


def help(rc=0):
    exename = sys.argv[0].rsplit("/", 1)[-1]
    print(
        "%s - Access REPL, perform remote file operations via MicroPython WebREPL protocol"
        % exename
    )
    print("Arguments:")
    print("  [-p password] <host>                            - Access the remote REPL")
    print("  [-p password] <host>:<remote_file> <local_file> - Copy remote file to local file")
    print("  [-p password] <local_file> <host>:<remote_file> - Copy local file to remote file")
    print("Examples:")
    print("  %s 192.168.4.1" % exename)
    print("  %s script.py 192.168.4.1:/another_name.py" % exename)
    print("  %s script.py 192.168.4.1:/app/" % exename)
    print("  %s -p password 192.168.4.1:/app/script.py ." % exename)
    sys.exit(rc)

def error(msg):
    print(msg)
    sys.exit(1)

def parse_remote(remote):
    host, fname = remote.rsplit(":", 1)
    if fname == "":
        fname = "/"
    port = 8266
    if ":" in host:
        host, port = host.split(":")
        port = int(port)
    return (host, port, fname)


# Very simplified client handshake, works for MicroPython's
# websocket server implementation, but probably not for other
# servers.
def client_handshake(sock):
    cl = sock.makefile("rwb", 0)
    cl.write(b"""\
GET / HTTP/1.1\r
Host: echo.websocket.org\r
Connection: Upgrade\r
Upgrade: websocket\r
Sec-WebSocket-Key: foo\r
\r
""")
    l = cl.readline()
#    print(l)
    while 1:
        l = cl.readline()
        if l == b"\r\n":
            break
#        sys.stdout.write(l)


def main():
    passwd = None
    for i in range(len(sys.argv)):
        if sys.argv[i] == '-p':
            sys.argv.pop(i)
            passwd = sys.argv.pop(i)
            break

    if len(sys.argv) not in (2, 3):
        help(1)

    if passwd is None:
        import getpass
        passwd = getpass.getpass()

    if len(sys.argv) > 2:
        if ":" in sys.argv[1] and ":" in sys.argv[2]:
            error("Operations on 2 remote files are not supported")
        if ":" not in sys.argv[1] and ":" not in sys.argv[2]:
            error("One remote file is required")

    if len(sys.argv) == 2:
        op = "repl"
        host, port, _ = parse_remote(sys.argv[1] + ":")
    elif ":" in sys.argv[1]:
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

    if True:
        print("op:%s, host:%s, port:%d, passwd:%s." % (op, host, port, passwd))
        if op in ("get", "put"):
            print(src_file, "->", dst_file)

    s = socket.socket()

    ai = socket.getaddrinfo(host, port)
    addr = ai[0][4]

    s.connect(addr)
    #s = s.makefile("rwb")
    client_handshake(s)

    ws = websocket(s)

    login(ws, passwd)
    print("Remote WebREPL version:", get_ver(ws))

    # Set websocket to send data marked as "binary"
    ws.ioctl(9, 2)

    if op == "repl":
        do_repl(ws)
    elif op == "get":
        get_file(ws, dst_file, src_file)
    elif op == "put":
        put_file(ws, src_file, dst_file)

    s.close()


if __name__ == "__main__":
    main()
