#!/usr/bin/env python
#
# complete rewrite of console webrepl client from aivarannamaa:
# https://forum.micropython.org/viewtopic.php?f=2&t=3124&p=29865#p29865
#
import sys
import readline
import getpass
import websocket

try:
    import thread
except ImportError:
    import _thread as thread
from time import sleep

try:                   # from https://stackoverflow.com/a/7321970
    input = raw_input  # Fix Python 2.x.
except NameError:
    pass


def help(rc=0):
    exename = sys.argv[0].rsplit("/", 1)[-1]
    print("%s - remote shell using MicroPython WebREPL protocol" % exename)
    print("Arguments:")
    print("  [-p password] [-dbg] [-r] <host> - remote shell (to <host>:8266)")
    print("Examples:")
    print("  %s 192.168.4.1" % exename)
    print("Special command control sequences:")
    print("  line with single characters")
    print("    'A' .. 'E' - use when CTRL-A .. CTRL-E needed")
    print('  just "exit" - end shell')
    sys.exit(rc)

inp = ""
raw_mode = False
normal_mode = True
paste_mode = False
prompt = "Password: "
prompt_seen = False
passwd = None
debug = False
redirect = False

for i in range(len(sys.argv)):
    if sys.argv[i] == '-p':
        sys.argv.pop(i)
        passwd = sys.argv.pop(i)
        break

for i in range(len(sys.argv)):
    if sys.argv[i] == '-dbg':
        sys.argv.pop(i)
        debug = True
        break

for i in range(len(sys.argv)):
    if sys.argv[i] == '-r':
        sys.argv.pop(i)
        redirect = True
        break

if len(sys.argv) != 2:
    help(1)


def on_message(ws, message):
    global inp
    global raw_mode
    global normal_mode
    global paste_mode
    global prompt
    global prompt_seen
    if len(inp) == 1 and ord(inp[0]) <= 5:
        inp = "\r\n" if inp != '\x04' else "\x04"
    while inp != "" and message != "" and inp[0] == message[0]:
        inp = inp[1:]
        message = message[1:]
    if message != "":
        if not(raw_mode) or inp != "\x04":
            inp = ""
    if raw_mode:
        if message == "OK":
            inp = "\x04\x04"
        elif message == "OK\x04":
            message = "OK"
            inp = "\x04"
        elif message == "OK\x04\x04":
            message = "OK"
            inp = ""
        elif message == "OK\x04\x04>":
            message = "OK>"
            inp = ""
    if debug:
        print("[%s,%d,%s]" % (message, ord(message[0]), inp))
    if inp == '' and prompt != '' and message.endswith(prompt):
        prompt_seen = True
        sys.stdout.write(message[:-len(prompt)])
    else:
        sys.stdout.write(message)
    sys.stdout.flush()
    if paste_mode and message == "=== ":
        inp = "\n"


def on_error(ws, error):
    sys.stdout.write("### error("+error+") ###\n")
    sys.stdout.flush()


def on_close(ws):
    sys.stdout.write("### closed ###\n")
    sys.stdout.flush()
    ws.close()
    sys.exit(1)


def on_open(ws):
    def run(*args):
        global input
        global inp
        global raw_mode
        global normal_mode
        global paste_mode
        global prompt
        global prompt_seen
        running = True
        do_input = getpass.getpass

        while running:
            while ws.sock and ws.sock.connected:
                while prompt and not(prompt_seen):
                    sleep(0.1)
                    if debug:
                        sys.stdout.write(":"+prompt+";")
                        sys.stdout.flush()
                prompt_seen = False

                if prompt == "Password: " and passwd is not None:
                    inp = passwd
                    sys.stdout.write("Password: ")
                    sys.stdout.flush()
                else:
                    inp = do_input(prompt)
                    if redirect:
                        sys.stdout.write(inp+"\n")
                        sys.stdout.flush()

                if len(inp) != 1 or inp[0] < 'A' or inp[0] > 'E':
                    inp += "\r\n"
                else:
                    inp = chr(ord(inp[0])-64)
                    if raw_mode:
                        if inp[0] == '\x02':
                            normal_mode = True
                            raw_mode = False
                    elif normal_mode:
                        if inp[0] == '\x01':
                            raw_mode = True
                            normal_mode = False
                        elif inp[0] == '\x05':
                            paste_mode = True
                            normal_mode = False
                    else:
                        if inp[0] == '\x03' or inp[0] == '\x04':
                            normal_mode = True
                            paste_mode = False

                do_input = getpass.getpass if raw_mode else input

                if prompt == "Password: ":  # initial "CTRL-C CTRL-B" injection
                    prompt = ""
                else:
                    prompt = "=== " if paste_mode else ">>> "[4*int(raw_mode):]

                if inp == "exit\r\n":
                    running = False
                    break
                else:
                    if ws.sock and ws.sock.connected:
                        ws.send(inp)
                        if prompt == "" and not(raw_mode):
                            inp += '\x03\x02'
                            ws.send('\x03\x02')
                    else:
                        running = False
            running = False
        ws.close()
        sys.exit(1)
    thread.start_new_thread(run, ())


if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://"+sys.argv[1]+":8266",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()

