# bh1750.py
class BH1750:
    PWR_DOWN = 0x00
    PWR_ON = 0x01
    RESET = 0x07
    CONT_HIRES_MODE = 0x10

    def __init__(self, i2c, addr=0x23):
        self.i2c = i2c
        self.addr = addr
        self.on()
        self.reset()

    def on(self):
        self.i2c.writeto(self.addr, bytes([self.PWR_ON]))

    def reset(self):
        self.i2c.writeto(self.addr, bytes([self.RESET]))

    def luminance(self):
        self.i2c.writeto(self.addr, bytes([self.CONT_HIRES_MODE]))
        data = self.i2c.readfrom(self.addr, 2)
        result = (data[0] << 8) | data[1]
        return result / 1.2
