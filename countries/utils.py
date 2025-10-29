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
    path = os.path.join("/tmp", "cache")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "summary.png")

def generate_summary_image(total_countries, top5, timestamp):
    """
    Create a summary PNG showing total countries, top 5 GDP countries, and refresh timestamp.
    """
    path = get_summary_image_path()

    # Create blank white image
    img = Image.new("RGB", (800, 500), color="white")
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_body = ImageFont.truetype("arial.ttf", 20)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Draw header
    draw.text((20, 20), "🌍 Country Summary Report", fill="black", font=font_title)
    draw.text((20, 70), f"Total Countries: {total_countries}", fill="black", font=font_body)

    # Draw top 5 GDP list
    draw.text((20, 120), "Top 5 Countries by Estimated GDP:", fill="black", font=font_body)

    y = 160
    if not top5:
        draw.text((40, y), "No GDP data available.", fill="gray", font=font_body)
    else:
        for c in top5:
            draw.text((40, y), f"- {c.name}: {round(c.estimated_gdp or 0, 2):,}", fill="blue", font=font_body)
            y += 30

    # Timestamp
    draw.text((20, 400), f"Last Refresh: {timestamp}", fill="black", font=font_body)

    # Save
    img.save(path, "PNG")
    return path
   

def get_now():
    """Return current UTC datetime (aware)."""
    return datetime.now(timezone.utc)

