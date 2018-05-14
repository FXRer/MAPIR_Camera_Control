import hid

dev = hid.device()
VENDOR_ID = 0x525
PRODUCT_ID = 0xa4ac
all_cameras = hid.enumerate(vendor_id = VENDOR_ID, product_id = PRODUCT_ID)
