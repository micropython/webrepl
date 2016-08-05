#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import getpass
try:
    import usocket as socket
except ImportError:
    import socket
from . import webrepl_client


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
    if fname == "":
        fname = "/"
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

    password = getpass.getpass()
    client = webrepl_client.WebREPLClient(password, host, port)
    client.connect()

    if op == "get":
        client.get_file(dst_file, src_file)
    elif op == "put":
        client.put_file(src_file, dst_file)


if __name__ == "__main__":
    main()
