"""
Show the current BTC price on an Action iPixel LED matrix, updated near-real-time,
with an up/down arrow (green/red) showing price direction since the last fetch.

Requirements:
    pip install pypixelcolor requests

IMPORTANT: run this once to confirm the exact color parameter name/format
send_text expects on your installed version:
    python -c "from pypixelcolor import Client; help(Client.send_text)"
If it's not called `color`, or expects a hex string instead of an (r,g,b)
tuple, adjust the `color=...` line in send_text() below accordingly.

If the up/down arrow characters show as blank boxes on your display (font
doesn't include them), change UP_ARROW/DOWN_ARROW below to "^" and "v".

Setup:
    1. Find your display's Bluetooth address (a UUID on macOS, a MAC on
       Linux/Android/Windows).
    2. Put that address in MAC_ADDRESS below.
    3. Run: python btc_ipixel.py
"""

import time
import requests
from pypixelcolor import Client, TextAnimation

MAC_ADDRESS = "20937C6B-771E-0791-5446-BE4037419563"  # confirmed working address
POLL_SECONDS = 15  # how often to check the price

UP_ARROW = "\u25B2"    # ▲  -- change to "^" if it doesn't render on your display
DOWN_ARROW = "\u25BC"  # ▼  -- change to "v" if it doesn't render on your display

GREEN = "00ff00"
RED = "ff0000"
NEUTRAL = "ffffff"  # used for the very first reading, no prior price yet


def get_btc_price() -> float:
    """Fetch current BTC price in USD from Binance's public ticker."""
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return float(response.json()["price"])


def main():
    last_sent_price = None      # last price we actually displayed (rounded)
    previous_raw_price = None   # last raw price we fetched, for direction comparison

    with Client(MAC_ADDRESS) as device:
        while True:
            try:
                price = get_btc_price()
                rounded = round(price)

                # Determine direction vs the last fetch (not just last displayed)
                if previous_raw_price is None:
                    arrow = ""
                    color = NEUTRAL
                elif price > previous_raw_price:
                    arrow = UP_ARROW
                    color = GREEN
                elif price < previous_raw_price:
                    arrow = DOWN_ARROW
                    color = RED
                else:
                    arrow = ""  # no change at all, no arrow
                    color = NEUTRAL

                previous_raw_price = price

                if rounded != last_sent_price:
                    text = f"{arrow} BTC ${rounded:,}" if arrow else f"BTC ${rounded:,}"

                    print(f"Sending: {text}  color={color}")
                    device.send_text(
                        text,
                        animation=TextAnimation.SCROLL_LEFT,
                        speed=90,
                        color=color,
                        char_height=16
                    )
                    last_sent_price = rounded
                else:
                    print(f"Price unchanged (${rounded:,}), skipping send")

            except Exception as e:
                print(f"Error: {e}")

            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()