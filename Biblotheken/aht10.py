# aht10.py
import time

class AHT10:
    def __init__(self, i2c, address=0x38):
        self.i2c = i2c
        self.address = address
        self._init_sensor()

    def _init_sensor(self):
        try:
            self.i2c.writeto(self.address, b'\xE1\x08\x00')
            time.sleep_ms(20)
        except OSError:
            pass  # Ignorieren, falls Sensor schon initialisiert

    def read_raw_data(self):
        self.i2c.writeto(self.address, b'\xAC\x33\x00')
        time.sleep_ms(80)
        raw = self.i2c.readfrom(self.address, 6)
        return raw

    def read(self):
        data = self.read_raw_data()
        if (data[0] & 0x80) != 0:
            raise Exception("Messung noch nicht abgeschlossen")

        humidity = (((data[1] << 16) | (data[2] << 8) | data[3]) >> 4) * 100 / 1048576
        temperature = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]) * 200 / 1048576 - 50
        return temperature, humidity
