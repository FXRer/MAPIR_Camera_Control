import os
import usb

os.umask(0)

dev = usb.core.find()
buf = [0] * 512
dev.write(endpoint = 0x81, data = buf, timeout = None )
