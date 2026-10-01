# -*- coding: utf-8 -*-
from __future__ import annotations
import os, subprocess, tempfile
from pathlib import Path

def texte_utile(texte: str) -> int:
    return sum(1 for c in texte if c.isalnum())

def ocr_image(chemin: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(chemin), lang="fra+eng") or ""
    except Exception:
        pass
    if os.name != "nt":
        return ""
    return _ocr_windows(chemin)

def _ocr_windows(chemin: Path) -> str:
    img = str(chemin.resolve()).replace("'", "''")
    ps = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
function Await($op, $t) {
  $m = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1
  } | Select-Object -First 1
  $task = $m.MakeGenericMethod($t).Invoke($null, @($op))
  $task.Wait() | Out-Null
  $task.Result
}
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime] | Out-Null
$path = '__IMG__'
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language('fr'))) }
if (-not $engine) { throw 'OCR Windows indisponible' }
$result = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$result.Text
""".replace("__IMG__", img)
    proc = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "OCR Windows en echec").strip()
        raise RuntimeError(err[:300])
    return (proc.stdout or "").strip()

def rendre_pages(pdf: Path, dossier: Path, echelle: float = 2.0):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    images = []
    try:
        for i in range(len(doc)):
            page = doc[i]
            bitmap = page.render(scale=echelle)
            pil = bitmap.to_pil()
            dest = dossier / f"page_{i+1:03d}.png"
            pil.save(dest, "PNG")
            images.append(dest)
            page.close()
    finally:
        doc.close()
    return images

def extraire_avec_ocr(pdf: Path, texte_deja: str = ""):
    if texte_utile(texte_deja) >= 40:
        return texte_deja, "texte"
    with tempfile.TemporaryDirectory() as tmp:
        images = rendre_pages(pdf, Path(tmp))
        pages = []
        for i, img in enumerate(images, 1):
            lu = ocr_image(img).strip()
            pages.append(f"--- Page {i} (OCR) ---\n{lu}")
        texte = "\n\n".join(pages).strip()
        if texte_utile(texte) < 8:
            raise RuntimeError("OCR sans resultat. Verifiez le pack de langue francais de reconnaissance optique Windows.")
        return texte, "ocr"
