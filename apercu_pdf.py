# -*- coding: utf-8 -*-
"""Aperçu de la première page PDF, sans logiciel supplémentaire."""
from pathlib import Path

import pypdfium2 as pdfium


def est_pdf(path: Path) -> bool:
    return Path(path).suffix.lower() == ".pdf"


def charger(path: Path, largeur: int, hauteur: int):
    doc = pdfium.PdfDocument(str(path))
    try:
        page = doc[0]
        try:
            largeur_page, hauteur_page = page.get_size()
            echelle = min(
                max(largeur, 200) / max(largeur_page, 1),
                max(hauteur, 200) / max(hauteur_page, 1),
            )
            image = page.render(scale=max(echelle, 0.4)).to_pil().convert("RGB")
        finally:
            page.close()
    finally:
        doc.close()
    image.thumbnail((max(largeur, 200), max(hauteur, 200)))
    return image
