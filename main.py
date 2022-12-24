from os import uname
from struct import pack

import aioble
import bluetooth
import uasyncio as asyncio
from machine import I2C, Pin, soft_reset
from micropython import const

from shtc3 import SHTC3

_ENV_SENSE_SVC_UUID = bluetooth.UUID(0x181A)
_ENV_TEMP_CHAR_UUID = bluetooth.UUID(0x2A6E)
_ENV_HUMID_CHAR_UUID = bluetooth.UUID(0x2A6F)
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)
_ADV_INTERVAL_US = const(250_000)

board_name = uname()[4].split()[0]

i2c = I2C(0, scl=Pin(8), sda=Pin(10))
shtc3 = SHTC3(i2c)

env_svc = aioble.Service(_ENV_SENSE_SVC_UUID)
temp_char = aioble.Characteristic(env_svc, _ENV_TEMP_CHAR_UUID, read=True, notify=True)
humid_char = aioble.Characteristic(
    env_svc, _ENV_HUMID_CHAR_UUID, read=True, notify=True
)
aioble.register_services(env_svc)


async def sensor_task():
    while True:
        (t, h) = await shtc3.measure()
        print(f"{t} degrees C, {t * 9 / 5 + 32} degrees F, {h}% humidity")
        temp_char.write(pack("<h", int(t * 100)), send_update=True)
        await asyncio.sleep(5)
        humid_char.write(pack("<H", int(h * 100)), send_update=True)
        await asyncio.sleep(10)


async def peripheral_task():
    try:
        while True:
            print(f"advertising as {board_name}")
            async with await aioble.advertise(
                _ADV_INTERVAL_US,
                name=board_name,
                services=[_ENV_SENSE_SVC_UUID],
                appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER,
            ) as connection:
                print(f"connected to {connection.device}")
                await connection.disconnected()
                print("disconnected")
    except asyncio.CancelledError:
        soft_reset()


async def main():
    tasks = (
        asyncio.create_task(sensor_task()),
        asyncio.create_task(peripheral_task()),
    )
    await asyncio.gather(*tasks)


asyncio.run(main())
