"""
BTC price on an Action iPixel 32x32 display, two rows:
  top row    : "BTC" + arrow (green up / red down since the last fetch)
  bottom row : the price, scrolling

The display has no multi-line text mode, so each update is rendered locally
as a small animated GIF (Pillow, same UNIFONT the library uses, 16px = clean
1x scale) and sent with send_image.

Requirements:
    pip install pypixelcolor requests
"""

import os
import tempfile
import time

import requests
from PIL import Image, ImageDraw, ImageFont
from pypixelcolor import Client
from pypixelcolor.lib.font_config import UNIFONT_PATH

MAC_ADDRESS = "20937C6B-771E-0791-5446-BE4037419563"  # confirmed working address
POLL_SECONDS = 3

SIZE = 32
FONT = ImageFont.truetype(UNIFONT_PATH, 16)
SCROLL_STEP_PX = 1      # pixels per frame; 1 is the slowest smooth scroll
FRAME_MS = 70           # per-frame delay; the display may ignore this

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

UP_ARROW = "▲"     # ▲
DOWN_ARROW = "▼"   # ▼


def get_btc_price() -> float:
    """Fetch current BTC price in USD from Binance's public ticker."""
    r = requests.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": "BTCUSDT"},
        timeout=10,
    )
    r.raise_for_status()
    return float(r.json()["price"])


def build_gif(path: str, price_text: str, arrow: str, color: tuple) -> None:
    """Render the two-row display to an animated GIF at `path`."""
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    text_w = int(measure.textlength(price_text, font=FONT))
    scrolls = text_w > SIZE
    offsets = range(SIZE, -text_w - 1, -SCROLL_STEP_PX) if scrolls else [(SIZE - text_w) // 2]

    frames = []
    for x in offsets:
        img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
        d = ImageDraw.Draw(img)
        d.fontmode = "1"  # no anti-aliasing: crisp pixels
        d.text((0, 0), "BTC", font=FONT, fill=WHITE)      # top row
        if arrow:
            d.text((24, 0), arrow, font=FONT, fill=color)
        d.text((x, 16), price_text, font=FONT, fill=color)  # bottom row
        frames.append(img)

    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=False,
        disposal=2,
    )


def main():
    last_sent_price = None
    previous_raw_price = None
    gif_path = os.path.join(tempfile.gettempdir(), "btc_ipixel.gif")

    with Client(MAC_ADDRESS) as device:
        while True:
            try:
                price = get_btc_price()
                rounded = round(price)

                if previous_raw_price is None or price == previous_raw_price:
                    arrow, color = "", WHITE
                elif price > previous_raw_price:
                    arrow, color = UP_ARROW, GREEN
                else:
                    arrow, color = DOWN_ARROW, RED
                previous_raw_price = price

                if rounded != last_sent_price:
                    text = f"${rounded:,}"
                    print(f"Sending: BTC {arrow} {text}")
                    build_gif(gif_path, text, arrow, color)
                    device.send_image(gif_path)
                    last_sent_price = rounded
                else:
                    print(f"Price unchanged (${rounded:,}), skipping send")

            except Exception as e:
                print(f"Error: {e}")

            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
