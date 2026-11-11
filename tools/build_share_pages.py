#!/usr/bin/env python3
"""Build one share page per property so links show the property's cover photo.

Viber, WhatsApp and Facebook build the link preview from the page's og:image
and ignore everything after "#", so every link to index.html#pNNN showed the
site logo. This script reads the property list (const P) from index.html and,
for every property, writes:

  NNN/index.html     a small page with the property's own title, price and
                     cover photo in its preview tags; visitors are sent on to
                     the property in the main page (../#pNNN) at once
  images/NNN/og.jpg  the cover photo (images/NNN/01.jpg) cropped to 1200x630

Share link format: https://n-kapitanov.github.io/properties/NNN/

Run it after any property is added, removed or changed (price, title, cover):
    python3 tools/build_share_pages.py
Pages of properties no longer in the list are deleted.
"""
import html
import pathlib
import re
import shutil
import sys

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://n-kapitanov.github.io/properties/"
OG_W, OG_H = 1200, 630
PHONE = "0878 760 894"


def field(block, name):
    m = re.search(name + r':"((?:[^"\\]|\\.)*)"', block)
    return m.group(1) if m else ""


def read_properties():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    start = src.index("const P=[")
    end = src.index("\n];", start)
    body = src[start:end]
    parts = re.split(r'\n \{id:"', body)[1:]
    props = []
    for part in parts:
        block = '{id:"' + part
        no = field(block, "no")
        if not re.fullmatch(r"\d{3}", no):
            sys.exit(f"Unexpected property number in: {block[:80]}")
        props.append({
            "id": field(block, "id"),
            "no": no,
            "short": field(block, "short"),
            "type": field(block, "type"),
            "place": field(block, "place"),
            "area": field(block, "area"),
            "price": field(block, "price"),
        })
    return props


def make_og_image(no):
    cover = ROOT / "images" / no / "01.jpg"
    if not cover.exists():
        return None
    out = ROOT / "images" / no / "og.jpg"
    with Image.open(cover) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, (OG_W, OG_H), Image.LANCZOS, centering=(0.5, 0.5))
        quality = 85
        while True:
            im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
            # WhatsApp skips preview images above ~300 KB
            if out.stat().st_size <= 280_000 or quality <= 60:
                break
            quality -= 5
    return out


def page(p, has_image):
    e = lambda s: html.escape(s, quote=True)
    title = f"{p['type']} · {p['short']}" if p["short"] else p["type"]
    bits = [x for x in (p["price"], p["area"], p["place"]) if x]
    desc = " · ".join(bits) + f". Ник Капитанов, ЕРА Вива, {PHONE}."
    url = f"{BASE}{p['no']}/"
    target = f"../#{p['id']}"
    img = f"{BASE}images/{p['no']}/og.jpg" if has_image else f"{BASE}brand/og-image.jpg"
    return f"""<!doctype html>
<html lang="bg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Купи имот с Ник">
<meta property="og:url" content="{e(url)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(img)}">
<meta property="og:image:width" content="{OG_W}">
<meta property="og:image:height" content="{OG_H}">
<meta property="og:locale" content="bg_BG">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="../brand/favicon.png">
<meta http-equiv="refresh" content="0; url={e(target)}">
<script>location.replace({target!r});</script>
</head>
<body style="font-family:system-ui,sans-serif;padding:24px">
<p><a href="{e(target)}">{e(title)}</a></p>
</body>
</html>
"""


def main():
    props = read_properties()
    keep = set()
    for p in props:
        has_image = make_og_image(p["no"]) is not None
        d = ROOT / p["no"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page(p, has_image), encoding="utf-8")
        keep.add(p["no"])
        print(f"{p['no']}  {BASE}{p['no']}/  {'cover' if has_image else 'NO COVER, logo used'}")
    for d in ROOT.iterdir():
        if d.is_dir() and re.fullmatch(r"\d{3}", d.name) and d.name not in keep:
            shutil.rmtree(d)
            og = ROOT / "images" / d.name / "og.jpg"
            if og.exists():
                og.unlink()
            print(f"{d.name}  removed (no longer in the list)")


if __name__ == "__main__":
    main()
