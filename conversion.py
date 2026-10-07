# -*- coding: utf-8 -*-
"""Conversion images et documents bureautique vers PDF."""
from __future__ import annotations
import io, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageSequence
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

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

def _dossiers_appli() -> list[Path]:
    dossiers = []
    if getattr(sys, "frozen", False):
        dossiers.append(Path(sys.executable).resolve().parent)
    dossiers.append(Path(__file__).resolve().parent)
    return dossiers

def trouver_soffice() -> str | None:
    relatifs = (
        Path("LibreOffice") / "program" / "soffice.com",
        Path("LibreOffice") / "program" / "soffice.exe",
        Path("LibreOffice") / "App" / "libreoffice" / "program" / "soffice.com",
        Path("LibreOffice") / "App" / "libreoffice" / "program" / "soffice.exe",
    )
    for base in _dossiers_appli():
        for rel in relatifs:
            candidat = base / rel
            if candidat.is_file():
                return str(candidat)
        dossier = base / "LibreOffice"
        if dossier.is_dir():
            for nom in ("soffice.com", "soffice.exe"):
                trouves = list(dossier.rglob(nom))
                if trouves:
                    return str(trouves[0])
    candidats = [
        r"C:\Program Files\LibreOffice\program\soffice.com",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
    ]
    for c in candidats:
        if os.path.isfile(c):
            return c
        found = shutil.which(c)
        if found:
            return found
    return None

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
                c.drawString(marge, y, ligne.encode("latin-1", "replace").decode("latin-1"))
                y -= interligne
                break
            coupe = len(ligne)
            while coupe > 0 and c.stringWidth(ligne[:coupe], "Helvetica", taille) > largeur:
                coupe -= 1
            if coupe <= 0:
                coupe = 1
            c.setFont("Helvetica", taille)
            c.drawString(marge, y, ligne[:coupe].encode("latin-1", "replace").decode("latin-1"))
            ligne = ligne[coupe:]
            y -= interligne
    c.save()

def convertir_rtf(source: Path, dest: Path) -> None:
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    brut = source.read_bytes().decode("latin-1", errors="replace")
    blocs = []
    courant = []
    gras = italique = souligne = False
    taille = 11

    def pousser(texte: str) -> None:
        if texte:
            courant.append(texte)

    i = 0
    n = len(brut)
    while i < n:
        car = brut[i]
        if car == "{":
            i += 1
            continue
        if car == "}":
            i += 1
            continue
        if car == "\\":
            if i + 1 < n and brut[i + 1] in "'":
                try:
                    pousser(bytes([int(brut[i + 2:i + 4], 16)]).decode("latin-1"))
                except Exception:
                    pass
                i += 4
                continue
            if i + 1 < n and brut[i + 1] == "u" and i + 2 < n and (brut[i + 2].isdigit() or brut[i + 2] == "-"):
                j = i + 2
                while j < n and (brut[j].isdigit() or brut[j] == "-"):
                    j += 1
                try:
                    val = int(brut[i + 2:j])
                    if val < 0:
                        val += 65536
                    pousser(chr(val))
                except Exception:
                    pass
                i = j + 1 if j < n and brut[j] == "?" else j
                continue
            j = i + 1
            while j < n and brut[j].isalpha():
                j += 1
            nom = brut[i + 1:j]
            k = j
            if k < n and (brut[k].isdigit() or brut[k] == "-"):
                k += 1
                while k < n and brut[k].isdigit():
                    k += 1
            val = brut[j:k]
            if k < n and brut[k] == " ":
                k += 1
            if nom in ("pict", "bin", "object", "objdata"):
                profondeur = 1
                i = k
                while i < n and profondeur:
                    if brut[i] == "{":
                        profondeur += 1
                    elif brut[i] == "}":
                        profondeur -= 1
                    i += 1
                continue
            if nom in ("par", "line"):
                blocs.append("".join(courant))
                courant = []
            elif nom == "tab":
                pousser("    ")
            elif nom == "b":
                gras = val != "0"
            elif nom == "i":
                italique = val != "0"
            elif nom == "ul":
                souligne = val != "0"
            elif nom == "ulnone":
                souligne = False
            elif nom == "fs" and val.lstrip("-").isdigit():
                taille = max(8, min(28, int(val) // 2))
            i = k
            continue
        pousser(car)
        i += 1
        if i > n:
            break
    if courant:
        blocs.append("".join(courant))
    style = ParagraphStyle("rtf", fontName="Times-Roman", fontSize=11, leading=14)
    doc = SimpleDocTemplate(str(dest), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    story = []
    for texte in blocs:
        propre = texte.replace("&", "&").replace("<", "<").replace(">", ">").strip()
        if not propre:
            story.append(Spacer(1, 8))
            continue
        if gras:
            propre = f"<b>{propre}</b>"
        if italique:
            propre = f"<i>{propre}</i>"
        if souligne:
            propre = f"<u>{propre}</u>"
        story.append(Paragraph(propre[:4000], style))
        story.append(Spacer(1, 6))
    if not story:
        story.append(Paragraph("(document RTF vide)", style))
    story.extend(_images_flowables(_images_rtf(source.read_bytes())[:12]))
    doc.build(story)

def _images_flowables(images: list[Image.Image]):
    from reportlab.platypus import Image as FlowImage, Spacer
    blocs = []
    for im in images:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        w, h = im.size
        max_w = 170 * mm
        echelle = min(1, max_w / max(w, 1))
        blocs.append(Spacer(1, 6))
        blocs.append(FlowImage(buf, width=w * echelle, height=h * echelle))
    return blocs

def _images_rtf(data: bytes) -> list[Image.Image]:
    texte = data.decode("latin-1", errors="replace")
    images = []
    pos = 0
    while len(images) < 12:
        i = texte.find("\\pict", pos)
        if i < 0:
            break
        j = texte.find("}", i)
        if j < 0:
            break
        morceau = texte[i:j]
        pos = j + 1
        if "pngblip" not in morceau and "jpegblip" not in morceau:
            continue
        hexa = "".join(c for c in morceau if c in "0123456789abcdefABCDEF")
        if len(hexa) < 32 or len(hexa) > 8_000_000:
            continue
        if len(hexa) % 2:
            hexa = hexa[:-1]
        try:
            im = Image.open(io.BytesIO(bytes.fromhex(hexa)))
            im.load()
            images.append(im)
        except Exception:
            continue
    return images

def _images_docx(source: Path) -> list[Image.Image]:
    import zipfile
    images = []
    with zipfile.ZipFile(source) as z:
        noms = [n for n in z.namelist() if n.startswith("word/media/")]
        for nom in sorted(noms):
            try:
                im = Image.open(io.BytesIO(z.read(nom)))
                im.load()
                images.append(im)
            except Exception:
                continue
    return images

def _images_doc(data: bytes) -> list[Image.Image]:
    images = []
    signatures = ((b"\xff\xd8\xff", b"\xff\xd9"), (b"\x89PNG\r\n\x1a\n", b"IEND\xaeB`\x82"))
    for debut, fin in signatures:
        pos = 0
        while True:
            i = data.find(debut, pos)
            if i < 0:
                break
            j = data.find(fin, i + len(debut))
            if j < 0:
                break
            blob = data[i:j + len(fin)]
            pos = j + len(fin)
            try:
                im = Image.open(io.BytesIO(blob))
                im.load()
                if im.size[0] > 16 and im.size[1] > 16:
                    images.append(im)
            except Exception:
                continue
    return images

def convertir_docx_avec_images(source: Path, dest: Path) -> None:
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    convertir_docx_texte(source, dest)
    images = _images_docx(source)
    if not images:
        return
    texte = ""
    try:
        import zipfile, xml.etree.ElementTree as ET
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with zipfile.ZipFile(source) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        texte = "\n".join("".join(t.text or "" for t in p.iter(ns + "t")) for p in root.iter(ns + "p"))
    except Exception:
        pass
    style = ParagraphStyle("docx", fontName="Times-Roman", fontSize=11, leading=14)
    doc = SimpleDocTemplate(str(dest), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    story = []
    for ligne in texte.splitlines():
        if ligne.strip():
            story.append(Paragraph(ligne.replace("&", "&").replace("<", "<"), style))
        else:
            story.append(Spacer(1, 8))
    story.extend(_images_flowables(images))
    doc.build(story)

def _poser_bibliotheques(programme: Path) -> None:
    noms = (
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "msvcp140.dll",
        "msvcp140_1.dll",
        "msvcp140_2.dll",
        "concrt140.dll",
    )
    sources = []
    for base in _dossiers_appli():
        sources.append(base / "vc")
        sources.append(base / "LibreOffice" / "program")
    windir = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if windir:
        sources.append(Path(windir) / "System32")
    for nom in noms:
        if (programme / nom).is_file():
            continue
        for dossier in sources:
            origine = dossier / nom
            if origine.is_file():
                try:
                    shutil.copy2(origine, programme / nom)
                except Exception:
                    pass
                break

def _bibliotheque_manquante(lanceur: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
        kernel.LoadLibraryExW.restype = ctypes.c_void_p
        if kernel.LoadLibraryExW(lanceur, None, 0x8):
            return ""
        code = ctypes.get_last_error()
        buffer = ctypes.create_unicode_buffer(512)
        kernel.FormatMessageW(0x1000, None, code, 0, buffer, 512, None)
        return buffer.value.strip()
    except Exception as e:
        return str(e)

def convertir_via_soffice(source: Path, dest: Path, soffice: str) -> None:
    programme = Path(soffice).resolve().parent
    binaire = programme / "soffice.bin"
    console = programme / "soffice.com"
    lanceur = str(binaire if binaire.is_file() else console if console.is_file() else Path(soffice).resolve())
    manquants = [
        nom for nom in ("soffice.bin", "sal3.dll", "fundamental.ini")
        if not (programme / nom).is_file()
    ]
    if manquants:
        raise RuntimeError(
            "Dossier LibreOffice incomplet, fichier manquant : "
            + ", ".join(manquants)
            + ". Il faut tout le dossier LibreOffice, pas seulement une partie."
        )
    _poser_bibliotheques(programme)
    detail_dll = _bibliotheque_manquante(lanceur)
    profil = Path(tempfile.mkdtemp(prefix="MEDICONF-lo-"))
    with tempfile.TemporaryDirectory() as tmp:
        travail = Path(tmp) / ("source" + source.suffix.lower())
        shutil.copy2(source, travail)
        ini = (programme / "fundamental.ini").resolve().as_uri()
        cmd = [
            lanceur,
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--nologo",
            "--nofirststartwizard",
            f"-env:UserInstallation={profil.resolve().as_uri()}",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            tmp,
            str(travail),
        ]
        env = os.environ.copy()
        env["PATH"] = str(programme) + os.pathsep + env.get("PATH", "")
        env["UNO_PATH"] = str(programme)
        env["URE_BOOTSTRAP"] = f"vnd.sun.star.pathname:{programme / 'fundamental.ini'}"
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(programme),
            env=env,
        )
        produits = [p for p in Path(tmp).glob("*.pdf") if p.is_file()]
        if not produits:
            detail = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
            code = proc.returncode
            if code in (3221225781, -1073741515):
                detail = "bibliothèque Windows introuvable (0xC0000135). " + (detail_dll or detail)
            raise RuntimeError(
                f"LibreOffice n'a produit aucun PDF (code {code})"
                + (f" : {detail[:220]}" if detail else "")
            )
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
    if ext == ".docx":
        images = _images_docx(source)
        try:
            import dxpdf
            dxpdf.convert_file(str(source), str(dest))
            if images:
                return f"DOCX converti avec dxpdf, {len(images)} image(s) incluse(s)."
            return "DOCX converti avec dxpdf, sans LibreOffice."
        except Exception:
            convertir_docx_avec_images(source, dest)
            return f"DOCX converti avec {len(images)} image(s)."
    if ext == ".doc":
        from apercu_doc import _texte_doc
        tmp = dest.with_suffix(".tmp.txt")
        tmp.write_text(_texte_doc(source), encoding="utf-8")
        try:
            convertir_texte(tmp, dest)
        finally:
            if tmp.exists():
                tmp.unlink()
        images = _images_doc(source.read_bytes())
        if images:
            from pypdf import PdfReader, PdfWriter
            from reportlab.platypus import SimpleDocTemplate
            annexe = dest.with_suffix(".images.pdf")
            doc = SimpleDocTemplate(str(annexe), pagesize=A4)
            doc.build(_images_flowables(images))
            writer = PdfWriter()
            for chemin in (dest, annexe):
                for page in PdfReader(str(chemin)).pages:
                    writer.add_page(page)
            with dest.open("wb") as f:
                writer.write(f)
            annexe.unlink(missing_ok=True)
        return f"DOC converti en texte avec {len(images)} image(s)."
    if ext == ".rtf":
        convertir_rtf(source, dest)
        return f"RTF converti avec {len(_images_rtf(source.read_bytes()))} image(s)."
    raise RuntimeError(f"Extension non geree : {ext}")
