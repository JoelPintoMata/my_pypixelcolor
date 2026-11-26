"""
BTC (EUR) and IWDA (EUR) on an Action iPixel 32x32 display, one per row:
  row 1: [arrow] BTC  EUR price   (arrow/color = direction since the last fetch)
  row 2: [arrow] IWDA EUR price   (arrow/color = up/down vs the previous close)

Both assets go through the SAME flow: a Ticker holds the fetch function, poll
interval, decimals and the arrow reference; every Ticker is updated, turned
into display cells, aligned and drawn identically. To add another asset, add
one more Ticker(...) to the list in main().

Layout: monospace UNIFONT (8px per character), so equal character counts line
up exactly. Prices are aligned on the decimal point. The arrow slot is a space
when the value hasn't moved.

Scrolling: the text starts at the left edge, pauses, scrolls until its END is
visible, pauses, then loops. The GIF is kept under MAX_FRAMES because the
display seems to cut off longer animations.

Data sources (both free, no API key):
  - BTC/EUR : Binance public ticker, pair BTCEUR
  - IWDA    : Yahoo Finance chart endpoint for IWDA.AS (Euronext Amsterdam, EUR).
              Unofficial endpoint; prices delayed ~15 min, only move while the
              exchange is open.

Requirements:
    pip install pypixelcolor requests
"""

import os
import tempfile
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests
from PIL import Image, ImageDraw, ImageFont
from pypixelcolor import Client
from pypixelcolor.lib.font_config import UNIFONT_PATH

MAC_ADDRESS = "20937C6B-771E-0791-5446-BE4037419563"
BTC_POLL_SECONDS = 30
IWDA_POLL_SECONDS = 60   # the fund only updates while the exchange is open

SIZE = 32
FONT = ImageFont.truetype(UNIFONT_PATH, 16)
SCROLL_STEP_PX = 1
FRAME_MS = 700
FRAME_REPEAT = 2     # copies of each scroll position; higher = slower scroll
HOLD_FRAMES = 10     # pause at the start and at the end of each pass
MAX_FRAMES = 200     # cap on GIF length; FRAME_REPEAT is lowered to fit
BOLD = True          # thicker letters (draws every glyph twice, 1px apart)

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

UP_ARROW = "▲"     # ▲
DOWN_ARROW = "▼"   # ▼
NO_CHANGE = " "         # blank arrow slot when the value hasn't moved
EURO = "€"         # €

# Near-invisible marker pixels (blue = 1 or 2 of 255). Each frame gets one so
# Pillow doesn't merge identical consecutive frames back into one.
MARKER_PIXELS = [(0, SIZE - 1), (SIZE - 1, SIZE - 1)]


# ---------------------------------------------------------------- data sources
# Every fetcher has the same shape: () -> (price, previous_close_or_None)

def fetch_btc_eur() -> tuple:
    r = requests.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": "BTCEUR"},
        timeout=10,
    )
    r.raise_for_status()
    return float(r.json()["price"]), None


def fetch_iwda() -> tuple:
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/IWDA.AS",
        params={"interval": "1d", "range": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},  # Yahoo rejects the default UA
        timeout=10,
    )
    r.raise_for_status()
    meta = r.json()["chart"]["result"][0]["meta"]
    return float(meta["regularMarketPrice"]), float(meta["chartPreviousClose"])


# ---------------------------------------------------------------------- ticker

@dataclass
class Ticker:
    label: str                           # text on the display, e.g. "BTC"
    fetch: Callable[[], tuple]           # () -> (price, previous_close or None)
    poll_seconds: float                  # how often to fetch this asset
    decimals: int                        # digits after the decimal point
    vs_previous_fetch: bool              # arrow vs last fetch (True) or vs previous close (False)
    price: Optional[float] = None
    reference: Optional[float] = None    # what the arrow compares against
    last_fetch: float = 0.0

    def update(self) -> None:
        """Fetch if due. On failure keep the last value."""
        if time.time() - self.last_fetch < self.poll_seconds:
            return
        self.last_fetch = time.time()
        try:
            price, previous_close = self.fetch()
        except Exception as e:
            print(f"{self.label} fetch failed (keeping last value): {e}")
            return
        self.reference = self.price if self.vs_previous_fetch else previous_close
        self.price = price

    def cells(self) -> tuple:
        """(arrow, color, integer_part, decimal_part) for display."""
        if self.price is None:
            return NO_CHANGE, WHITE, "--", ""
        arrow, color = direction(self.price, self.reference)
        whole, _, frac = f"{self.price:,.{self.decimals}f}".partition(".")
        return arrow, color, f"{EURO}{whole}", f".{frac}" if frac else ""


def direction(current, reference):
    """Return (arrow, color) for current vs reference."""
    if reference is None or current == reference:
        return NO_CHANGE, WHITE
    return (UP_ARROW, GREEN) if current > reference else (DOWN_ARROW, RED)


# ---------------------------------------------------------------------- layout

def build_rows(tickers: list) -> list:
    """One (text, color) row per ticker, all columns aligned across rows."""
    cells = [t.cells() for t in tickers]
    label_w = max(len(t.label) for t in tickers)
    int_w = max(len(c[2]) for c in cells)
    dec_w = max(len(c[3]) for c in cells)
    return [
        (f"{arrow}{t.label:<{label_w}} {whole:>{int_w}}{frac:<{dec_w}}", color)
        for t, (arrow, color, whole, frac) in zip(tickers, cells)
    ]


# ------------------------------------------------------------------- rendering

def render_frame(rows: list, x: int) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"  # crisp pixels, no anti-aliasing
    for i, (text, color) in enumerate(rows):
        d.text((x, i * 16), text, font=FONT, fill=color)
        if BOLD:  # double-strike: same text again, 1px to the right
            d.text((x + 1, i * 16), text, font=FONT, fill=color)
    return img


def build_gif(path: str, rows: list) -> None:
    """rows = [(text, color), (text, color)]; each row is 16px tall."""
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    text_w = max(int(measure.textlength(t, font=FONT)) for t, _ in rows)
    text_w += 1 if BOLD else 0

    # Scroll from x=0 until the END of the text reaches the right edge.
    end_x = min(0, SIZE - text_w)
    xs = list(range(0, end_x, -SCROLL_STEP_PX)) + [end_x]
    if end_x < 0:
        xs = [0] * HOLD_FRAMES + xs + [end_x] * HOLD_FRAMES

    repeat = max(1, min(FRAME_REPEAT, MAX_FRAMES // len(xs)))

    frames = []
    for x in xs:
        img = render_frame(rows, x)
        for _ in range(repeat):
            frame = img.copy()
            marker = (0, 0, len(frames) % 2 + 1)
            for pos in MARKER_PIXELS:
                if frame.getpixel(pos) == (0, 0, 0):
                    frame.putpixel(pos, marker)
                    break
            frames.append(frame)

    frames[0].save(
        path, save_all=True, append_images=frames[1:],
        duration=FRAME_MS, loop=0, optimize=False, disposal=2,
    )


# ------------------------------------------------------------------------ main

def main():
    tickers = [
        Ticker("BTC", fetch_btc_eur, BTC_POLL_SECONDS, decimals=0, vs_previous_fetch=True),
        Ticker("IWDA", fetch_iwda, IWDA_POLL_SECONDS, decimals=2, vs_previous_fetch=False),
    ]
    tick_seconds = min(t.poll_seconds for t in tickers)
    gif_path = os.path.join(tempfile.gettempdir(), "btc_iwda_ipixel.gif")
    last_rows = None

    with Client(MAC_ADDRESS) as device:
        while True:
            try:
                for t in tickers:
                    t.update()
                rows = build_rows(tickers)

                # Only re-send when what's displayed changed
                if rows != last_rows:
                    print("Sending:", " | ".join(text for text, _ in rows))
                    build_gif(gif_path, rows)
                    device.send_image(gif_path)
                    last_rows = rows
                else:
                    print("Unchanged, skipping send")

            except Exception as e:
                print(f"Error: {e}")

            time.sleep(tick_seconds)


if __name__ == "__main__":
    main()
