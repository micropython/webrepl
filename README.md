WebREPL client for MicroPython
==============================

This repository contains the WebREPL client and related tools, for
accessing a MicroPython REPL (interactive prompt) over WebSockets.

To start WebREPL terminal client, clone or download this repository
(in full) and open webrepl.html in a browser. Recent versions of
Firefox and Chrome (or Chromium) are supported.

The latest version of the client is also hosted online at
http://micropython.org/webrepl (note: while it's hosted online,
all interaction with your boards still happen locally in your
own network).

At this time, WebREPL client cannot be accessed over HTTPS connections.
This is due to not widely published policy that HTTPS pages may
access only WSS (WebSocket Secure) protocol. This is somewhat
similar to warnings issued when e.g. an HTTPS page loads an image
over plain HTTP. However, in case of WebSockets, some browsers
don't even issue a user-visible warning, and others may word it
confusingly, so it's hard to understand that it applies to WebSocket
connections. As WebREPL is intended to be used only within a user's
local network, HTTPS isn't strictly required, and not accessing
webrepl.html over HTTPS is a suggested workaround.

WebREPL file transfer
---------------------

WebREPL protocol includes experimental support for file transfer.
This feature is currently in alpha and has known issues on systems
which have it enabled (ESP8266).

To use WebREPL file transfer capabilities, a separate command line
utility is provided, webrepl_cli.py (file transfer is not supported
via webrepl.html client). Run

    webrepl_cli.py --help

to see usage information. Note that there can be only one active
WebREPL connection, so while webrepl.html is connected to device,
webrepl_cli.py can't transfer files, and vice versa.


WebREPL shell
---------------------

webrepl_client.py provides remote shell using MicroPython WebREPL protocol, and runs with Python 2 as well as Python 3. With wireless connection to MicroPython it is OTA shell (Over-the-air), the main difference to screen WebREPL terminal session.

Run just command for usage information:

    $ ./webrepl_client.py 
    webrepl_client.py - remote shell using MicroPython WebREPL protocol
    Arguments:
      [-p password] [-dbg] [-r] <host> - remote shell (to <host>:8266)
    Examples:
      webrepl_client.py 192.168.4.1
      webrepl_client.py -p abcd 192.168.4.1
      webrepl_client.py -p abcd -r 192.168.4.1 < <(sleep 1 && echo "...")
    Special command control sequences:
      line with single characters
        'A' .. 'E' - use when CTRL-A .. CTRL-E needed
      just "exit" - end shell
    $

* "-p" option allows to pass password instead of entering via keyboard, allowing for automation.
* "-r" option tells webrepl_client.py that input will be provided by redirection, and that command lines need to be printed (not needed when input is done via keyboard). See last sample execution on how to paste in python code from file and use (without need to upload a module before).
* "-dbg" option enables additional debug output in case webrepl_client.py has a problem and is not needed normally.

Previous section on only one active WebREPL connection applies here as well. So you can run shell, then exit, then upload a modified module with webrepl_cli.py to MicroPython, login again into shell and finally reload the module in shell.


Input is invisible on password entry for WebREPL session, as well as in raw mode (raw mode is not available in webrepl.html). Commands can be edited on input, and command history is available.

CTRL-A, CTRL-B, CTRL-C, CTRL-D and CTRL-E on empty line switch between modes. For webrepl_client.py these have to be entered by A+ENTER, B+ENTER, C+ENTER, D+ENTER, E+ENTER.

Normal mode is correct, as well as paste mode. Raw mode has invisible input, and output ">" is followed by "OK>" for every press of CTRL-D. Only difference to screen session is, that each completed line produces a new line.

Although not documented in raw mode python help, CTRL-D is needed (as in paste mode) before CTRL-B to switch to normal mode, to commit the input lines sofar. CTRL-D can be pressed multiple times before CTRL-B. Beware that you need to have at least one line of input present, otherwise CTRL-D will do a soft reset on target platform.

Soft reset on target platform (by machine.reset() or by CTRL-D on empty input line) hangs webrepl_client.py session as well as webrepl.html browser session.

Because Micropython issue https://github.com/micropython/micropython/issues/4196 initial WebREPL prompt on (re)connect is always ">>> ", regardless of real mode (raw/normal/paste). Since webrepl_client.py needs to wait for prompt being received from target in order to do correct and editable input via "do_input(prompt)", issue 4196 is problematic. Currently this issue is resolved by automatically injecting "CTRL-C CTRL-B" after password has been entered, ending always in normal mode. Because of the "CTRL-B" you see the MicoPython version string message on (re)connect. The injection also helps on terminating endless loops, which was possible before fix of issue 1. Now on endless loop, press "CTRL-C" to terminate webrepl_client.py and reconnect again. The initial injected "CTRL-C" will stop the endless loop and provide REPL prompt.

Sample session with mode changes and invisible password and raw mode input:

    $ ./webrepl_client.py 192.168.4.1
    Password: 
    
    WebREPL connected
    >>> 
    >>> 
    MicroPython v1.9.4-481-g3cd2c281d on 2018-09-04; ESP module with ESP8266
    Type "help()" for more information.
    >>> A
    raw REPL; CTRL-B to exit
    >
    
    OK>
    MicroPython v1.9.4-481-g3cd2c281d on 2018-09-04; ESP module with ESP8266
    Type "help()" for more information.
    >>> a
    42
    >>> E
    paste mode; Ctrl-C to cancel, Ctrl-D to finish
    === a=43
    === C
    >>> a
    42
    >>> E
    paste mode; Ctrl-C to cancel, Ctrl-D to finish
    === a=43
    === D
    
    >>> a
    43
    >>> 4**3**2
    262144
    >>> exit
    ### closed ###
    $

Sample session with password on command line and redirect:

    $ ./webrepl_client.py -p abcd -r 192.168.4.1 < <(sleep 1 && echo "E" && cat sc.py && echo -e "D\nc(7)\nexit")
    Password:
    WebREPL connected
    >>>
    >>>
    MicroPython v1.9.4-481-g3cd2c281d on 2018-09-04; ESP module with ESP8266
    Type "help()" for more information.
    >>> E
    paste mode; Ctrl-C to cancel, Ctrl-D to finish
    === def s(x):
    ===     return x*x
    === def c(x):
    ===     return x*s(x)
    === D
    
    >>> c(7)
    343
    >>> exit
    ### closed ###
    $


Both, webrepl_cli.py as well as webrepl_client.py, do not run on MicroPython. Using danni's uwebsockets repo a simple (OTA) shell can be run from one MicroPython module on a second MicroPython module:
https://forum.micropython.org/viewtopic.php?f=2&p=30829#p30829


Technical details
-----------------

WebREPL is the latest standard (in the sense of an Internet RFC) for
communicating with and controlling a MicroPython-based board. Following
were the requirements for the protocol design:

1. Single connection/channel, multiplexing terminal access, filesystem
access, and board control.

2. Network ready and Web technologies ready (allowing access directly
from a browser with an HTML-based client).

Based on these requirements, WebREPL uses a single connection over
[WebSocket](https://en.wikipedia.org/wiki/WebSocket) as a transport
protocol. Note that while WebREPL is primarily intended for network
(usually, wireless) connection, due to its single-connection,
multiplexed nature, the same protocol can be used over a lower-level,
wired connection like UART, SPI, I2C, etc.

Few other traits of WebREPL:

1. It is intended (whenever possible) to work in background, i.e.
while WebREPL operations are executed (like a file transfer), normal
REPL/user application should continue to run and be responsive
(though perhaps with higher latency, as WebREPL operations may
take its share of CPU time and other system resources). (Some
systems may not allow such background operation, and then WebREPL
access/operations will be blocking).

2. While it's intended to run in background, like a Unix daemon,
it's not intended to support multiple, per-connection sessions.
There's a single REPL session, and this same session is accessible
via different media, like UART or WebREPL. This also means that
there's usually no point in having more than one WebREPL connection
(multiple connections would access the same session), and a
particular system may actually limit number of concurrent
connections to ease implementation and save system resources.

WebREPL protocol consists of 2 sub-protocols:

* Terminal protocol

This protocol is finalized and is very simple in its nature, akin
to Telnet protocol. WebSocket "text"-flagged messages are used to
communicate terminal input and output between a client and a WebREPL-
enabled device (server). There's a guaranteed password prompt, which
can be detected by the appearance of characters ':', ' ' (at this
point, server expected a password ending with '\n' from client).
If you're interested in developing a 3rd-party application to communicate
using WebREPL terminal protocol, the information above should be enough
to implement it (or feel free to study implementation of the official
clients in this repository).

* File transfer/board control protocol

This protocol uses WebSocket "binary"-flagged messages. At this point,
this protocol is in early research/design/proof-of-concept phase. The
only available specification of it is the reference code implementation,
and the protocol is subject to frequent and incompatible changes.
The `webrepl_cli.py` module mentioned above intended to be both a
command-line tool and a library for 3rd-party projects to use, though
it may not be there yet. If you're interested in integrating WebREPL
transfer/control capabilities into your application, please submit
a ticket to GitHub with information about your project and how it is
useful to MicroPython community, to help us prioritize this work.

While the protocol is (eventually) intended to provide full-fledged
filesystem access and means to control a board (all subject to
resource constraints of a deeply embedded boards it's intended to
run on), currently, only "get file" and "put file" operations are
supported. As above, sharing information with us on features you
miss and how they can be helpful to the general MicroPython
community will help us prioritize our plans. If you're interested
in reducing wait time for new features, you're also welcome to
contribute to their implementation. Please start with discussing
the design first, and with small changes and improvements. Please
keep in mind that WebREPL is just one of the many features on which
MicroPython developers work, so having sustainable (vs revolutionary)
development process is a must to have long-term success.
