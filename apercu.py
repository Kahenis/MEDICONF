# -*- coding: utf-8 -*-
"""Miniatures sans logiciel supplémentaire : images, PDF, RTF, DOC, DOCX."""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
CONVERTIBLES = IMAGES | {".rtf", ".doc", ".docx", ".odt", ".txt", ".pdf"}


def est_convertible(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in CONVERTIBLES


def _police(taille: int):
    for nom in ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def _page_texte(titre: str, texte: str, largeur: int = 640, hauteur: int = 820) -> Image.Image:
    im = Image.new("RGB", (largeur, hauteur), "#ffffff")
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, largeur - 1, hauteur - 1), outline="#c5c9ce")
    draw.rectangle((0, 0, largeur, 42), fill="#1f4e79")
    draw.text((16, 10), titre[:70], fill="#ffffff", font=_police(16))
    y = 58
    font = _police(15)
    for ligne in (texte or "(aucun texte lisible)").splitlines():
        while ligne:
            morceau = ligne[:78]
            ligne = ligne[78:]
            draw.text((18, y), morceau, fill="#222222", font=font)
            y += 22
            if y > hauteur - 24:
                return im
    return im


def _texte_docx(path: Path) -> str:
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    lignes = []
    for para in root.iter(ns + "p"):
        lignes.append("".join(t.text or "" for t in para.iter(ns + "t")))
    return "\n".join(lignes).strip()


def _texte_rtf(path: Path) -> str:
    brut = path.read_bytes().decode("latin-1", errors="replace")
    brut = brut.replace("\\par", "\n").replace("\\line", "\n")
    brut = re.sub(r"\\'[0-9a-fA-F]{2}", " ", brut)
    brut = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", brut)
    brut = brut.replace("{", "").replace("}", "")
    return re.sub(r"[ \t]+\n", "\n", brut).strip()


def _texte_doc(path: Path) -> str:
    data = path.read_bytes()
    morceaux = []
    i = 0
    while i < len(data) - 4:
        if data[i + 1] == 0 and 32 <= data[i] < 127:
            j = i
            chars = []
            while j < len(data) - 1 and data[j + 1] == 0 and 32 <= data[j] < 127:
                chars.append(chr(data[j]))
                j += 2
            if len(chars) > 12:
                morceaux.append("".join(chars))
            i = j
        else:
            i += 1
    return "\n".join(morceaux[:40])


def miniature(path: Path, largeur: int = 640, hauteur: int = 820) -> Image.Image:
    ext = path.suffix.lower()
    if ext in IMAGES:
        im = Image.open(path)
        im = im.convert("RGB")
        im.thumbnail((largeur, hauteur))
        return im
    if ext == ".pdf":
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(path))
        page = doc[0]
        im = page.render(scale=1.4).to_pil().convert("RGB")
        page.close()
        doc.close()
        im.thumbnail((largeur, hauteur))
        return im
    if ext == ".docx":
        return _page_texte(path.name, _texte_docx(path), largeur, hauteur)
    if ext == ".rtf":
        return _page_texte(path.name, _texte_rtf(path), largeur, hauteur)
    if ext == ".doc":
        return _page_texte(path.name, _texte_doc(path), largeur, hauteur)
    if ext == ".txt":
        return _page_texte(path.name, path.read_text(encoding="utf-8", errors="replace")[:4000], largeur, hauteur)
    if ext == ".odt":
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("content.xml"))
        textes = [t.text or "" for t in root.iter() if t.tag.endswith("}p")]
        return _page_texte(path.name, "\n".join(textes)[:4000], largeur, hauteur)
    return _page_texte(path.name, "Aperçu non disponible pour ce type.", largeur, hauteur)
