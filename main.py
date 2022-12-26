from os import uname
from struct import pack
from time import ticks_ms

import aioble
import bluetooth
import uasyncio as asyncio
from aioble.core import ble
from machine import I2C, Pin
from micropython import const

from shtc3 import SHTC3

_ENV_SENSE_SVC_UUID = bluetooth.UUID(0x181A)
_ENV_TEMP_CHAR_UUID = bluetooth.UUID(0x2A6E)
_ENV_HUMID_CHAR_UUID = bluetooth.UUID(0x2A6F)
_ADV_INTERVAL_US = const(250_000)

board_name = uname()[4].split()[0].encode()

i2c = I2C(0, scl=Pin(8), sda=Pin(10))
shtc3 = SHTC3(i2c)

env_svc = aioble.Service(_ENV_SENSE_SVC_UUID)
temp_char = aioble.Characteristic(env_svc, _ENV_TEMP_CHAR_UUID, read=True, notify=True)
humid_char = aioble.Characteristic(
    env_svc, _ENV_HUMID_CHAR_UUID, read=True, notify=True
)
aioble.register_services(env_svc)


async def main():
    eddystone_tlm = bytearray(31)
    eddystone_tlm[0] = 0x02  # len
    eddystone_tlm[1] = 0x01  # flags
    eddystone_tlm[2] = 0x06

    eddystone_tlm[3] = 0x04  # len
    eddystone_tlm[4] = 0x09  # name
    eddystone_tlm[5] = board_name[0]
    eddystone_tlm[6] = board_name[1]
    eddystone_tlm[7] = board_name[2]

    eddystone_tlm[8] = 0x03  # len
    eddystone_tlm[9] = 0x03  # service uuid
    eddystone_tlm[10] = 0xAA
    eddystone_tlm[11] = 0xFE

    eddystone_tlm[12] = 0x11  # len
    eddystone_tlm[13] = 0x16  # service data
    eddystone_tlm[14] = 0xAA
    eddystone_tlm[15] = 0xFE

    eddystone_tlm[16] = 0x20  # telm
    # eddystone_tlm[17] = 0x00  # version

    # eddystone_tlm[18] = 0x00  # vbat
    # eddystone_tlm[19] = 0x00  # vbat

    # eddystone_tlm[20] = 0x00  # temp
    # eddystone_tlm[21] = 0x00  # temp

    # eddystone_tlm[22] = 0x00  # adv pdu cnt
    # eddystone_tlm[23] = 0x00  # adv pdu cnt
    # eddystone_tlm[24] = 0x00  # adv pdu cnt
    # eddystone_tlm[25] = 0x00  # adv pdu cnt

    # eddystone_tlm[26] = 0x00  # timestamp
    # eddystone_tlm[27] = 0x00  # timestamp
    # eddystone_tlm[28] = 0x00  # timestamp
    # eddystone_tlm[29] = 0x00  # timestamp

    while True:
        (t, h) = await shtc3.measure()
        print(f"{t} degrees C, {t * 9 / 5 + 32} degrees F, {h}% humidity")

        temp_char.write(pack("<h", int(t * 100)), send_update=True)
        humid_char.write(pack("<H", int(h * 100)), send_update=True)

        eddystone_tlm[20] = int(t)
        eddystone_tlm[21] = int((t % 1) * 256.0)

        centiseconds = ticks_ms() // 100
        eddystone_tlm[26] = centiseconds >> 24
        eddystone_tlm[27] = centiseconds >> 16
        eddystone_tlm[28] = centiseconds >> 8
        eddystone_tlm[29] = centiseconds

        ble.gap_advertise(_ADV_INTERVAL_US, adv_data=eddystone_tlm)

        await asyncio.sleep(15)


asyncio.run(main())
