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
