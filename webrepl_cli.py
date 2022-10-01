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

        def write(self, data, text=False):
            OpCode = 1 if text else 2
            l = len(data)
            if l < 126:
                # TODO: hardcoded "binary" type
                hdr = struct.pack(">BB", 0x80 + OpCode, l)
            else:
                hdr = struct.pack(">BBH", 0x80 + OpCode, 126, l)
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
        c = ws.read(1, text_ok = True)
        if c == b":":
            assert ws.read(1, text_ok = True) == b" "
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
    exename = os.path.basename(sys.argv[0])

    print(
        '{exename} - Perform remote file operations using MicroPython WebREPL protocol'
        '\n'
        'Syntax:\n'
        '    webrepl_cli.py [options] [src dst]\n'
        '\n'
        'Options:\n'
        '    --passwd pw    Set the login password\n'
        '    --host host    Set the host when using commands\n'
        '    --cmd cmd      Execute the command cmd in the server\n'
        '    --verbose, -v  Set verbose\n'

        'File copy:\n'

        '       <host>:<remote_file> <local_file> - Copy remote file to local file\n'
        '       <local_file> <host>:<remote_file> - Copy local file to remote file\n'
        '\n'
        'Examples:\n'
        '  {exename} script.py 192.168.4.1:/another_name.py\n'
        '  {exename} script.py 192.168.4.1:/app/\n'
        '  {exename} 192.168.4.1:/app/script.py\n'

        '\n'
        .format(exename = exename))

    sys.exit(rc)

def query_response(ws, cmd, verbose=False):
    '''Single line query to single line response. May be used as rpc'''
#    ws.write((cmd+'\r').encode(), frame=WEBREPL_FRAME_TXT)
    ws.write((cmd+'\r').encode(), text=True)
    if verbose:
      print(cmd)

    if '\r' in cmd or '\n' in cmd:
      raise runtime_error('Currently no support for multi line queries!')

    Response = b''
    while True:
      c = ws.read(1, text_ok = True)
      Response += c

      # Finish on prompt
      if Response[-5:]==b'\n>>> ':
        break

    # Cleanup the response and return it
    return (Response[Response.index(b'\n')+1:-6]  # Get rid of input line
            .decode()                             # decode into python string
            .replace('\r',''))                    # Get rid of \r

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

# A class for communicating with the esp8266
class WebreplCLI:
    def __init__(self,
                 host = '192.168.0.1',
                 port = 8266,
                 verbose = False,
                 password = 'esp8266',
                 dont_connect = False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.password = password
        if not dont_connect:
            self.connect()

    def connect(self):
        self.s = socket.socket()
    
        ai = socket.getaddrinfo(self.host, self.port)
        addr = ai[0][4]
    
        self.s.connect(addr)
        #s = s.makefile("rwb")
        client_handshake(self.s)
    
        self.ws = websocket(self.s)
    
        login(self.ws, self.password)
        ver = get_ver(self.ws)
        if self.verbose:
            print("Remote WebREPL version:", ver)
    
        # Set websocket to send data marked as "binary"
        self.ws.ioctl(9, 2)
        if self.verbose:
            print('Connected')

    def close(self):
        self.s.close()

    def command(self, cmd):
        return query_response(self.ws, cmd)

    def get_file(self, local_file, remote_file):
        return get_file(self.ws, local_file, remote_file)

    def put_file(self, local_file, remote_file):
        return put_file(self.ws, local_file, remote_file)
            
def main():
    passwd = None
    cmd = None
    host = '192.168.0.1'
    port = 8266
    verbose = False

    argp = 1
    while argp < len(sys.argv) and sys.argv[argp][0] == '-':
        S_ = sys.argv[argp]
        argp+=1

        if S_ == '--help':
            help(0)
            exit(0)
            
        if S_ == '--passwd' or S_=='-p':
            passwd = sys.argv[argp]
            argp+=1
            continue

        if S_ == '--host' or S_=='-h':
            host = sys.argv[argp]
            argp+=1
            continue

        if S_ == '--cmd':
            cmd = sys.argv[argp]
            argp+=1
            continue

        error('Unknown option: ' + S_ + '!')

    if cmd is None:
        if len(sys.argv) < argp+2:
            print('Need at least two arguments for file copy!')
            exit(-1)

        if ":" in sys.argv[argp] and ":" in sys.argv[argp+1]:
            error("Operations on 2 remote files are not supported")
        if ":" not in sys.argv[argp] and ":" not in sys.argv[argp+1]:
            error("One remote file is required")
    
        if ":" in sys.argv[argp]:
            op = "get"
            host, port, src_file = parse_remote(sys.argv[argp])
            dst_file = sys.argv[argp+1]
            if os.path.isdir(dst_file):
                basename = src_file.rsplit("/", 1)[-1]
                dst_file += "/" + basename
        else:
            op = "put"
            host, port, dst_file = parse_remote(sys.argv[argp+1])
            src_file = sys.argv[argp]
            if dst_file[-1] == "/":
                basename = src_file.rsplit("/", 1)[-1]
                dst_file += basename
    
        if 1:
            print(op, host, port)
            print(src_file, "->", dst_file)
    else:
        if host is None:
            error('Must specify port for executing commands!')

    if passwd is None:
      import getpass
      passwd = getpass.getpass()

    wc = WebreplCLI(host = host,
                    port = port,
                    password = passwd,
                    verbose = verbose)

    if cmd is not None:
        res = wc.command(cmd)
        if res:
          print(res)
    elif op == "get":
       wc.get_file(dst_file, src_file)
    elif op == "put":
       wc.put_file(src_file, dst_file)

    wc.close()

if __name__ == "__main__":
    main()
