# -*- coding: utf-8 -*-
"""Aperçu texte des documents bureautiques, sans logiciel supplémentaire."""
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DOCUMENTS = {".doc", ".docx", ".rtf"}


def est_document(path: Path) -> bool:
    return Path(path).suffix.lower() in DOCUMENTS


def _police(taille: int):
    for nom in ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


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
            if len(chars) > 8:
                morceaux.append("".join(chars))
            i = max(j, i + 1)
        else:
            i += 1
    return "\n".join(morceaux[:30])


def texte(path: Path) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".docx":
        return _texte_docx(path)
    if ext == ".rtf":
        return _texte_rtf(path)
    if ext == ".doc":
        return _texte_doc(path)
    return ""


def charger(path: Path, largeur: int, hauteur: int) -> Image.Image:
    largeur = max(largeur, 240)
    hauteur = max(hauteur, 180)
    contenu = texte(path) or "(aucun texte lisible dans ce document)"
    im = Image.new("RGB", (largeur, hauteur), "#ffffff")
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, largeur - 1, hauteur - 1), outline="#c5c9ce")
    draw.rectangle((0, 0, largeur, 36), fill="#1f4e79")
    draw.text((12, 8), Path(path).name[:48], fill="#ffffff", font=_police(14))
    y = 48
    font = _police(13)
    for ligne in contenu.splitlines():
        if not ligne.strip():
            y += 10
            continue
        reste = ligne
        while reste:
            morceau = reste[:72]
            reste = reste[72:]
            draw.text((12, y), morceau, fill="#222222", font=font)
            y += 18
            if y > hauteur - 16:
                return im
    return im
