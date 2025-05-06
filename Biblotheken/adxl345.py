import time

class ADXL345:
    ADDRESS = 0x53

    def __init__(self, i2c):
        self.i2c = i2c
        self.i2c.writeto_mem(self.ADDRESS, 0x2D, b'\x08')  # Wake-up
        time.sleep(0.1)

    def read(self):
        data = self.i2c.readfrom_mem(self.ADDRESS, 0x32, 6)
        x = int.from_bytes(data[0:2], 'little', signed=True)
        y = int.from_bytes(data[2:4], 'little', signed=True)
        z = int.from_bytes(data[4:6], 'little', signed=True)
        return (x / 256, y / 256, z / 256)
