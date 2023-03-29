#!/usr/bin/env python3

# This script transforms webrepl.html into a javascript string wrapped in
# document.write, which allows the device to serve a very simple page
# containing
# <base href="https://url-to-static-host/"></base>
# <script src="webrepl_content.js"></script>

import datetime

with open("webrepl.html", "r") as f_in:
    with open("webrepl_content.js", "w") as f_out:
        f_out.write("// {}\n".format(datetime.datetime.now().isoformat()))
        f_out.write("document.write(\"")
        f_out.write(f_in.read().replace("\"", "\\\"").replace("\n", "\\n"))
        f_out.write("\");")
