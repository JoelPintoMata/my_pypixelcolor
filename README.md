# my_pypixelcolor

Python scripts that show live prices (BTC/EUR, and IWDA in v3) on an Action
iPixel 32x32 LED matrix over Bluetooth Low Energy (BLE), using the
[pypixelcolor](https://pypi.org/project/pypixelcolor/) library.

## Setup

```bash
python3 -m venv ./venv
source ./venv/bin/activate
pip install pypixelcolor requests bleak
```

## Step 1: find your display's address with `scan_ble.py`

### Why

Every script connects to the display by its Bluetooth address, set in
`MAC_ADDRESS` at the top of the file. You need your own display's address, and
it can be hard to find:

- Many iPixel displays don't advertise a name, so they don't show up as
  "iPixel" in a normal Bluetooth device list.
- On macOS the address isn't the device's real MAC. CoreBluetooth gives each
  device a UUID instead (for example `20937C6B-771E-0791-5446-BE4037419563`).
  On Linux and Windows it's a normal MAC address (`AA:BB:CC:DD:EE:FF`).

### What it does

`scan_ble.py` listens for nearby BLE devices for 10 seconds and prints one
line per device:

- **address:** what you put in `MAC_ADDRESS`
- **name:** the advertised name, or `None` if the device doesn't send one
- **rssi:** signal strength in dBm. Closer to 0 means stronger, which usually
  means closer.
- **services:** the advertised service UUIDs

Devices that advertise a service UUID starting with `0000fa`, the service
used by the iPixel/BK-Light protocol, are marked
`<-- possible iPixel match!`.

### How to use it

1. Power on the display and place it next to your computer.
2. Close the iPixel phone app, or turn off your phone's Bluetooth. The
   display may not advertise while it's connected to another device.
3. Run the scan:

   ```bash
   python3 scan_ble.py
   ```

   Example output:

   ```
   Scanning for 10 seconds...
   4F1A...C2D9  name=None  rssi=-88  services=[]
   20937C6B-771E-0791-5446-BE4037419563  name=None  rssi=-41  services=['0000fa00-0000-1000-8000-00805f9b34fb']  <-- possible iPixel match!
   ```

4. Copy the address of the flagged device into `MAC_ADDRESS` in the script
   you want to run.

If no device is flagged:

- Look for the device with the strongest RSSI (closest to 0).
- Run the scan again with the display farther away. The line whose RSSI
  changes the most is your display.
- Power-cycle the display, then scan again.

**macOS:** the first scan may ask for Bluetooth permission for your terminal
or VS Code. If you see `No BLE devices found.`, check
System Settings → Privacy & Security → Bluetooth and allow the app you're
running Python from.

## Step 2: run a display script

```bash
python3 my_pypixel_v3.py
```

| Script | What it shows |
| --- | --- |
| `my_pypixel_v1.py` | BTC price as text, with a green/red arrow for the direction since the last fetch |
| `my_pypixel_v2.py` | The same, drawn as a custom GIF |
| `my_pypixel_v3.py` | Two scrolling rows: BTC/EUR (Binance) and IWDA (Yahoo Finance, ~15 min delayed) |

All three scripts poll free public APIs and need no API key. Stop a script
with `Ctrl+C`.
