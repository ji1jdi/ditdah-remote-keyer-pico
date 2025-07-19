import asyncio
import heapq
import network
import socket
import settings
from machine import Pin
from time import ticks_ms
from wifi import WIFI
from emitter import Emitter
from keyer import Keyer
from keyout import KeyOut
from led import LED

key_in  = Pin(settings.KEYIN_PIN, Pin.IN, Pin.PULL_UP)
key_out = KeyOut(Pin(settings.KEYOUT_PIN, Pin.OUT))
led     = LED(Pin("LED", Pin.OUT))

tx_emitter = Emitter()
rx_emitter = Emitter()

tx_keyer = Keyer(tx_emitter)
rx_keyer = Keyer(rx_emitter)

tx_emitter.on("on", led.on)
tx_emitter.on("off", led.off)

if settings.RUN_MODE == "RIG":
    tx_emitter.on("on", key_out.on)
    tx_emitter.on("off", key_out.off)

rx_emitter.on("on", led.on)
rx_emitter.on("off", led.off)
rx_emitter.on("on", key_out.on)
rx_emitter.on("off", key_out.off)

def setup_wifi():
    wifi = WIFI(settings.WIFI_MODE)

    wifi.deactivate()
    wifi.activate()

    ifconfig = (settings.HOST_ADDR, settings.SUBNET_MASK,
                settings.GATEWAY_ADDR, settings.DNS_ADDR)

    if settings.WIFI_MODE == "AP":
        wifi.config(essid=settings.WIFI_SSID, password=settings.WIFI_KEY)
        wifi.ifconfig(ifconfig)
        print("AP mode started", wifi.ifconfig())
    else:
        wifi.ifconfig(ifconfig)
        wifi.connect(settings.WIFI_SSID, settings.WIFI_KEY)
        print("STA mode started", wifi.ifconfig())

keying_buf = []
keying_buf_lock = asyncio.Lock()

async def rx():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", settings.PORT))
    s.setblocking(False)

    while True:
        try:
            data, _ = s.recvfrom(1024)
            if len(data) != 3:
                print("invalid data length")
                continue

            seq         = data[0] << 8 | data[1]
            keying_time = ticks_ms() + settings.KEYING_DELAY
            keying      = data[2]

            async with keying_buf_lock:
                heapq.heappush(keying_buf, (seq, keying_time, keying))
        except OSError:
            pass

        await asyncio.sleep(settings.TASK_DELAY)

async def tx():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0

    while True:
        try:
            d = bytes([
                (seq >> 8) & 0xff,
                seq & 0xff,
                not key_in.value()
            ])

            seq = (seq + 1) % 2**16

            n = s.sendto(d, (settings.PEER_ADDR, settings.PORT))
        except OSError:
            pass

        await asyncio.sleep(settings.TASK_DELAY)

async def loop():
    while True:
        if key_in.value() == 0:
            tx_keyer.on()
        else:
            tx_keyer.off()

        await asyncio.sleep(settings.TASK_DELAY)

async def keyer():
    while True:
        now = ticks_ms()

        async with keying_buf_lock:
            while keying_buf and keying_buf[0][1] <= now:
                _, _, keying = heapq.heappop(keying_buf)

                if keying:
                    rx_keyer.on()
                else:
                    rx_keyer.off()

        await asyncio.sleep(settings.TASK_DELAY)

async def main():
    led.on()

    setup_wifi()

    led.off()

    if settings.RUN_MODE == "OPERATOR":
        await asyncio.gather(loop(), tx())
    else:
        await asyncio.gather(loop(), rx(), keyer())

if __name__ == "__main__":
    asyncio.run(main())
