# -*- coding: utf-8 -*-
"""Aperçu des images à partir du chemin stocké sur la ligne."""
from pathlib import Path

from PIL import Image

IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".jfif", ".ico"}


def est_image(path: Path) -> bool:
    return Path(path).suffix.lower() in IMAGES


def charger(path: Path, largeur: int, hauteur: int) -> Image.Image:
    im = Image.open(path)
    im.load()
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    im.thumbnail((max(largeur, 120), max(hauteur, 120)))
    return im
