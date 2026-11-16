#!/usr/bin/env python3
"""Save the whole screen of an X display as PNG (works with Xvfb):  xshot.py :98 out.png
Uses `xwd` (x11-apps) and Pillow; prints the mean colour so an all-black capture is easy to spot."""
import struct
import subprocess
import sys

from PIL import Image

disp, out = sys.argv[1], sys.argv[2]
d = subprocess.run(["xwd", "-root", "-silent", "-display", disp], capture_output=True, check=True).stdout
h = struct.unpack(">25I", d[:100])
header_size, width, height, byte_order, bpp, bytes_per_line, ncolors = h[0], h[4], h[5], h[7], h[11], h[12], h[19]
offset = header_size + ncolors * 12
data = d[offset:offset + bytes_per_line * height]
lsb = byte_order == 0
if bpp == 32:
    im = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA" if lsb else "ARGB", bytes_per_line, 1).convert("RGB")
elif bpp == 24:
    im = Image.frombuffer("RGB", (width, height), data, "raw", "BGR" if lsb else "RGB", bytes_per_line, 1)
else:
    sys.exit("unsupported bits per pixel: %d" % bpp)
im.save(out)
mean = im.resize((1, 1), Image.BOX).getpixel((0, 0))
print(out, im.size, "mean RGB", mean)
