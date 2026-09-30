# -*- coding: utf-8 -*-
"""Conversion images et documents bureautique vers PDF."""
from __future__ import annotations
import io, os, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageSequence
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from moteurs import (
    dossier_application,
    trouver_word,
    trouver_soffice,
    convertir_via_word,
)

EXTENSIONS_IMAGES = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff",
    ".webp", ".ico", ".jfif", ".heic", ".heif",
}
EXTENSIONS_DOCS = {".txt", ".rtf", ".doc", ".docx", ".odt"}
EXTENSIONS_PDF = {".pdf"}
EXTENSIONS_OK = EXTENSIONS_IMAGES | EXTENSIONS_DOCS | EXTENSIONS_PDF

def est_image(chemin: Path) -> bool:
    return chemin.suffix.lower() in EXTENSIONS_IMAGES

def est_document(chemin: Path) -> bool:
    return chemin.suffix.lower() in EXTENSIONS_DOCS

def est_pdf(chemin: Path) -> bool:
    return chemin.suffix.lower() in EXTENSIONS_PDF

def nom_pdf_cible(source: Path, dossier_cible: Path, source_racine: Path | None,
                  conserver_arbo: bool, conflit: str) -> Path:
    if conserver_arbo and source_racine and source_racine.is_dir():
        try:
            rel = source.parent.relative_to(source_racine)
        except ValueError:
            rel = Path()
        dest_dir = dossier_cible / rel
    else:
        dest_dir = dossier_cible
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (source.stem + ".pdf")
    if dest.exists():
        if conflit == "ecraser":
            return dest
        if conflit == "renommer":
            i = 2
            while True:
                candidat = dest_dir / f"{source.stem}_{i}.pdf"
                if not candidat.exists():
                    return candidat
                i += 1
    return dest

def _preparer_image(path: Path, compression: bool, qualite: int) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        fond = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        if alpha is not None:
            fond.paste(img.convert("RGB"), mask=alpha)
        else:
            fond.paste(img.convert("RGB"))
        img = fond
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if compression:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=max(40, min(95, int(qualite))), optimize=True)
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        img.load()
    return img

def convertir_image(source: Path, dest: Path, compression: bool, qualite: int) -> None:
    img0 = Image.open(source)
    frames = []
    if getattr(img0, "is_animated", False) and source.suffix.lower() in {".gif", ".tif", ".tiff"}:
        for frame in ImageSequence.Iterator(img0):
            fr = frame.convert("RGBA")
            fond = Image.new("RGB", fr.size, (255, 255, 255))
            fond.paste(fr.convert("RGB"), mask=fr.split()[-1])
            if compression:
                buf = io.BytesIO()
                fond.save(buf, format="JPEG", quality=max(40, min(95, int(qualite))), optimize=True)
                buf.seek(0)
                fond = Image.open(buf).convert("RGB")
                fond.load()
            frames.append(fond)
    else:
        frames = [_preparer_image(source, compression, qualite)]
    c = canvas.Canvas(str(dest), pagesize=A4)
    pw, ph = A4
    for im in frames:
        w, h = im.size
        max_w, max_h = pw - 20 * mm, ph - 20 * mm
        scale = min(max_w / w, max_h / h)
        dw, dh = w * scale, h * scale
        x = (pw - dw) / 2
        y = (ph - dh) / 2
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85 if compression else 95)
        buf.seek(0)
        c.drawImage(ImageReader(buf), x, y, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
        c.showPage()
    c.save()

def convertir_texte(source: Path, dest: Path) -> None:
    texte = source.read_text(encoding="utf-8", errors="replace")
    c = canvas.Canvas(str(dest), pagesize=A4)
    pw, ph = A4
    marge = 18 * mm
    y = ph - marge
    taille = 10
    interligne = 13
    largeur = pw - 2 * marge
    for brut in texte.splitlines() or [""]:
        ligne = brut.replace("\t", "    ")
        while True:
            if y < marge + interligne:
                c.showPage()
                y = ph - marge
            if c.stringWidth(ligne, "Helvetica", taille) <= largeur:
                c.setFont("Helvetica", taille)
                c.drawString(marge, y, ligne)
                y -= interligne
                break
            coupe = len(ligne)
            while coupe > 0 and c.stringWidth(ligne[:coupe], "Helvetica", taille) > largeur:
                coupe -= 1
            if coupe <= 0:
                coupe = 1
            c.setFont("Helvetica", taille)
            c.drawString(marge, y, ligne[:coupe])
            ligne = ligne[coupe:]
            y -= interligne
    c.save()

def convertir_via_soffice(source: Path, dest: Path, soffice: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", tmp, str(source)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        produits = list(Path(tmp).glob("*.pdf"))
        if not produits:
            err = (proc.stderr or proc.stdout or "LibreOffice n'a produit aucun PDF").strip()
            raise RuntimeError(err[:400])
        shutil.copy2(produits[0], dest)

def convertir_docx_texte(source: Path, dest: Path) -> None:
    import zipfile, xml.etree.ElementTree as ET
    NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(source) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    lignes = []
    for p in root.iter(NS + "p"):
        parts = [t.text or "" for t in p.iter(NS + "t")]
        lignes.append("".join(parts))
    tmp = dest.with_suffix(".tmp.txt")
    tmp.write_text("\n".join(lignes), encoding="utf-8")
    try:
        convertir_texte(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()

def convertir_fichier(source: Path, dest: Path, compression: bool, qualite: int) -> str:
    ext = source.suffix.lower()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if ext == ".pdf":
        if Path(source).resolve() != Path(dest).resolve():
            shutil.copy2(source, dest)
        return "PDF copie sans reconversion."
    if ext in EXTENSIONS_IMAGES:
        if ext in {".heic", ".heif"}:
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except Exception as e:
                raise RuntimeError("Format HEIC non supporte (module pillow-heif absent).") from e
        convertir_image(source, dest, compression, qualite)
        return ""
    if ext == ".txt":
        convertir_texte(source, dest)
        return ""
    if ext in {".rtf", ".doc", ".docx"} and trouver_word():
        convertir_via_word(source, dest)
        return "Converti avec Microsoft Word."
    soffice = trouver_soffice()
    if ext in {".rtf", ".doc", ".docx", ".odt"} and soffice:
        convertir_via_soffice(source, dest, soffice)
        base = str(dossier_application()).lower()
        via = "LibreOffice portable" if soffice.lower().startswith(base) else "LibreOffice"
        return f"Converti avec {via}."
    if ext == ".docx":
        convertir_docx_texte(source, dest)
        return "DOCX converti en texte (Word / LibreOffice absents : mise en page simplifiee)."
    if ext in {".rtf", ".doc", ".odt"}:
        raise RuntimeError(
            "Aucun moteur bureautique trouve. "
            "Placez LibreOfficePortable a cote de MEDICONF.exe ou installez Word."
        )
    raise RuntimeError(f"Extension non geree : {ext}")
