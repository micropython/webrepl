#!/usr/bin/env python
#
# based on console webrepl client from aivarannamaa:
# https://forum.micropython.org/viewtopic.php?f=2&t=3124&p=29865#p29865
#
# + on_message() flush fix
# + "-s" silent option
# + check for ws.sock for graceful endings in some situations
# + try/except for graceful ending on CTRL-C
# + now runs with python v2 as well as v3
# + replace "-s" by "-v" option, make silent the default, "-v" for raw mode
# + help()
# + pep8online.com no warnings/errors
# needs update after next commits
#
import sys
import readline
import getpass
import websocket
import threading
from time import sleep

try:                   # from https://stackoverflow.com/a/7321970
    input = raw_input  # Fix Python 2.x.
except NameError:
    pass
do_input = getpass.getpass

def help(rc=0):
    exename = sys.argv[0].rsplit("/", 1)[-1]
    print("%s - remote shell using MicroPython WebREPL protocol" % exename)
    print("Arguments:")
    print("  <host> - open remote shell (to <host>:8266)")
    print("Examples:")
    print("  %s 192.168.4.1" % exename)
    print("Special command control sequences:")
    print('  just "exit" - end shell')
    sys.exit(rc)

inp = ""
if len(sys.argv) not in (2, 2):
    help(1)

def on_message(ws, message):
    global inp
    while (inp != "") and (message != "") and (inp[0] == message[0]):
        inp = inp[1:]
        message = message[1:]
    if (message != ""):
        inp = ""
    sys.stdout.write(message)
    sys.stdout.flush()


def on_close(ws):
    print("### closed ###")

websocket.enableTrace(False)
ws = websocket.WebSocketApp("ws://"+sys.argv[1]+":8266", on_message=on_message,
                            on_close=on_close)
wst = threading.Thread(target=ws.run_forever)
wst.daemon = True
wst.start()

conn_timeout = 5
while ws.sock and not ws.sock.connected and conn_timeout:
    sleep(1)
    conn_timeout -= 1

try:
    while ws.sock and ws.sock.connected:
        inp = ((do_input('') + "\r\n")
               .replace("\\x01", "\x01")    # switch to raw mode
               .replace("\\x02", "\x02")    # switch to normal mode
               .replace("\\x03", "\x03")    # interrupt
               .replace("\\x04", "\x04"))   # end of command in raw mode
        do_input = input

        if inp == "exit" + "\r\n":
            ws.close()
        else:
            if ws.sock and ws.sock.connected:
                ws.send(inp)
except KeyboardInterrupt:
    ws.close()
    sys.exit(1)
