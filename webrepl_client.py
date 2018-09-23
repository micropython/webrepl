#!/usr/bin/env python
#
# complete rewrite of console webrepl client from aivarannamaa:
# https://forum.micropython.org/viewtopic.php?f=2&t=3124&p=29865#p29865
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
    print("  line with single characters")
    print("    'A' .. 'E' - CTRL-A .. CTRL-E")
    print('  just "exit" - end shell')
    sys.exit(rc)

if len(sys.argv) not in (2, 2):
    help(1)

running = True
inp = ""
raw_mode = False
normal_mode = True
paste_mode = False


def on_message(ws, message):
    global inp
    if (len(inp) == 1) and ord(inp[0]) <= 5:
        inp = "\r\n" if (inp != '\x04') else "\x04"
    while (inp != "") and (message != "") and (inp[0] == message[0]):
        inp = inp[1:]
        message = message[1:]
    if (message != ""):
        if not(raw_mode) or (inp != "\x04"):
            inp = ""
    if raw_mode:
        if (message == "OK"):
            inp = "\x04\x04"
        elif (message == "OK\x04"):
            message = "OK"
            inp = "\x04"
        elif (message == "OK\x04\x04"):
            message = "OK"
            inp = ""
        elif (message == "OK\x04\x04>"):
            message = "OK>"
            inp = ""
    if True:
        sys.stdout.write(message)
    else:
        print("[%s,%d,%s]" % (message, ord(message[0]), inp))  # for debug
    sys.stdout.flush()
    if paste_mode and (message == "=== "):
        inp = "\n"


def on_close(ws):
    sys.stdout.write("### closed ###\n")
    sys.stdout.flush()
    ws.close()
    sys.exit(1)

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

while running:
    try:
        while ws.sock and ws.sock.connected:
            inp = do_input('')

            if (len(inp) != 1) or ((inp[0] < 'A') and (inp[0] > '\x05')) or (inp[0] > 'E'):
                inp += "\r\n"
            else:
                if (inp[0] > '\x05'):
                    inp = chr(ord(inp[0])-64) 
                if raw_mode:
                    if (inp[0] == '\x02'):
                        normal_mode = True
                        raw_mode = False
                elif (normal_mode):
                    if (inp[0] == '\x01'):
                        raw_mode = True
                        normal_mode = False
                    elif (inp[0] == '\x05'):
                        paste_mode = True
                        normal_mode = False

            do_input = getpass.getpass if raw_mode else input

            if inp == "exit\r\n":
                running = False
                break
            else:
                if ws.sock and ws.sock.connected:
                    ws.send(inp)
                else:
                    running = False
        running = False
    except KeyboardInterrupt:
        if ws.sock and ws.sock.connected:
            ws.send("\x03")
            if paste_mode:
                normal_mode = True
                paste_mode = False
        else:
            running = False
    except EOFError:
        if ws.sock and ws.sock.connected:
            ws.send("\x04")
            if paste_mode:
                normal_mode = True
                paste_mode = False
        else:
            running = False
ws.close()
sys.exit(1)

