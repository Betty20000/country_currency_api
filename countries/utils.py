import requests
import random
import io
from datetime import  datetime, timezone
datetime.now(timezone.utc)
from PIL import Image, ImageDraw, ImageFont
import os


COUNTRIES_API = 'https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies'
EXCHANGE_API = 'https://open.er-api.com/v6/latest/USD'


def fetch_countries():
    resp = requests.get(COUNTRIES_API, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_exchange_rates():
    resp = requests.get(EXCHANGE_API, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # API returns 'rates' mapping
    return data.get('rates', {})


def make_multiplier():
    return random.randint(1000, 2000)

def get_summary_image_path():
    return os.path.abspath('cache/summary.png')

def generate_summary_image(total_countries, top5, timestamp, out_path='cache/summary.png'):
    # Create a simple PNG with Pillow summarising results
    width, height = 1200, 800
    im = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)

    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 24)
    except Exception:
        font = ImageFont.load_default()

    y = 20
    draw.text((20, y), f'Total countries: {total_countries}', font=font)
    y += 40
    draw.text((20, y), f'Last refreshed: {timestamp}', font=font)
    y += 60
    draw.text((20, y), 'Top 5 countries by estimated GDP:', font=font)
    y += 36

    for i, c in enumerate(top5, start=1):
        line = f"{i}. {c.name} — {c.estimated_gdp:,.2f} {c.currency_code or ''}"
        draw.text((30, y), line, font=font)
        y += 30
        if y > height - 40:
            break

    # ensure cache dir exists and save
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path)
    return out_path




def get_now():
    """Return current UTC datetime (aware)."""
    return datetime.now(timezone.utc)

