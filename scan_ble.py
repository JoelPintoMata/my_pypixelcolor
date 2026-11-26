"""
Scan for nearby BLE devices and show RSSI + advertised service UUIDs,
to help identify an iPixel display that doesn't broadcast its name.

Requirements:
    pip install bleak

Run:
    python scan_ble.py

The iPixel/BK-Light protocol uses a service UUID starting with 0000fa00.
Devices matching that will be flagged. Otherwise, look at RSSI (closer to
0 = stronger signal = likely nearby) and try moving the display closer
or power-cycling it, then re-run.
"""

import asyncio
from bleak import BleakScanner

IPIXEL_SERVICE_HINT = "0000fa"  # known iPixel/BK-Light service prefix


async def main():
    print("Scanning for 10 seconds...")
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)

    if not devices:
        print("No BLE devices found.")
        return

    for address, (device, adv) in devices.items():
        name = device.name or "None"
        rssi = adv.rssi if adv.rssi is not None else "?"
        services = list(adv.service_uuids) if adv.service_uuids else []
        flag = ""
        if any(s.startswith(IPIXEL_SERVICE_HINT) for s in services):
            flag = "  <-- possible iPixel match!"
        print(f"{address}  name={name}  rssi={rssi}  services={services}{flag}")


if __name__ == "__main__":
    asyncio.run(main())