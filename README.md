WebREPL client for MicroPython
==============================

This repository contains the WebREPL client and related tools, for
accessing a MicroPython REPL (interactive prompt) over WebSockets.

To start WebREPL terminal client, clone or download this repository
(in full) and open webrepl.html in a browser. Recent versions of
Firefox and Chrome (or Chromium) are supported.

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
