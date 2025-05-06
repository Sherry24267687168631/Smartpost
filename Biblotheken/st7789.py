import framebuf
import time

class ST7789:
    def __init__(self, spi, dc, cs, rst, width, height):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.width = width
        self.height = height

        self.buffer = bytearray(self.width * self.height * 2)
        self.framebuf = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.RGB565)

        self.dc.init(self.dc.OUT, value=0)
        self.cs.init(self.cs.OUT, value=1)
        self.rst.init(self.rst.OUT, value=1)

        self.reset()
        self.init_display()

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

    def write_cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def write_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(bytearray([data]))
        self.cs.value(1)

    def init_display(self):
        self.write_cmd(0x36)
        self.write_data(0x00)

        self.write_cmd(0x3A)
        self.write_data(0x55)

        self.write_cmd(0x11)
        time.sleep_ms(120)

        self.write_cmd(0x29)

    def show(self):
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data((self.width - 1) >> 8)
        self.write_data((self.width - 1) & 0xFF)

        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data((self.height - 1) >> 8)
        self.write_data((self.height - 1) & 0xFF)

        self.write_cmd(0x2C)

        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(self.buffer)
        self.cs.value(1)
