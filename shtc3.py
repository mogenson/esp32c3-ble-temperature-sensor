from struct import unpack
from time import sleep_ms

import uasyncio as asyncio
from machine import I2C
from micropython import const

_SHTC3_ADDR = const(0x70)
_SHTC3_CHIP_ID = const(0x807)
_SHTC3_READ_ID = const(0xEFC8)
_SHTC3_RESET = const(0x805D)
_SHTC3_READ_TEMP_HUMID = const(0x7866)


class SHTC3:
    def __init__(self, i2c: I2C):
        self._i2c = i2c
        self.reset()
        self._chip_id = self.get_chip_id()
        if self._chip_id != _SHTC3_CHIP_ID:
            raise RuntimeError("Failed to find SHTC3 sensor")

    def _write_command(self, command: int) -> None:
        buf = bytearray(2)
        buf[0] = command >> 8
        buf[1] = command & 0xFF
        self._i2c.writeto(_SHTC3_ADDR, buf)

    def reset(self) -> None:
        self._write_command(_SHTC3_RESET)
        sleep_ms(1)

    def get_chip_id(self) -> int:
        self._write_command(_SHTC3_READ_ID)
        sleep_ms(1)
        buf = self._i2c.readfrom(_SHTC3_ADDR, 3)
        return unpack(">H", buf)[0] & 0x083F

    async def measure(self) -> (float, float):
        temperature, humidity = None, None

        self._write_command(_SHTC3_READ_TEMP_HUMID)
        await asyncio.sleep_ms(15)
        buf = self._i2c.readfrom(_SHTC3_ADDR, 6)

        temp_data = buf[0:2]
        temp_crc = buf[2]
        humid_data = buf[3:5]
        humid_crc = buf[5]

        if temp_crc != self._crc8(temp_data) or humid_crc != self._crc8(humid_data):
            return (temperature, humidity)

        raw_temp = unpack(">H", temp_data)[0]
        raw_temp = ((4375 * raw_temp) >> 14) - 4500
        temperature = raw_temp / 100.0

        raw_humid = unpack(">H", humid_data)[0]
        raw_humid = (625 * raw_humid) >> 12
        humidity = raw_humid / 100.0

        return (temperature, humidity)

    @staticmethod
    def _crc8(buf: bytearray) -> int:
        crc = 0xFF
        for byte in buf:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF
