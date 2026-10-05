# -*- coding: utf-8 -*-
"""Aperçu de la première page PDF, sans logiciel supplémentaire."""
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw


def est_pdf(path: Path) -> bool:
    return Path(path).suffix.lower() == ".pdf"


def charger(path: Path, largeur: int, hauteur: int):
    largeur = max(int(largeur), 200)
    hauteur = max(int(hauteur), 200)
    doc = pdfium.PdfDocument(str(path))
    try:
        if len(doc) < 1:
            raise ValueError("PDF sans page")
        page = doc[0]
        try:
            largeur_page, hauteur_page = page.get_size()
            echelle = min(largeur / max(largeur_page, 1), hauteur / max(hauteur_page, 1))
            image = page.render(scale=max(echelle, 0.5)).to_pil().convert("RGB")
        finally:
            page.close()
    finally:
        doc.close()
    image.thumbnail((largeur, hauteur))
    return image
