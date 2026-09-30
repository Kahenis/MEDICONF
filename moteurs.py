# -*- coding: utf-8 -*-
from __future__ import annotations
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

def dossier_application() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

_cache_word = False
_cache_soffice = False

def trouver_word():
    global _cache_word
    if _cache_word is not False:
        return _cache_word
    if os.name != "nt":
        _cache_word = None
        return None
    which = shutil.which("WINWORD.EXE")
    if which:
        _cache_word = which
        return which
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidats = []
    for racine in (pf, pf86):
        office = Path(racine) / "Microsoft Office"
        if office.is_dir():
            candidats.extend(office.glob("root/Office*/WINWORD.EXE"))
            candidats.extend(office.glob("Office*/WINWORD.EXE"))
    for c in candidats:
        if Path(c).is_file():
            _cache_word = str(c)
            return _cache_word
    _cache_word = None
    return None

def trouver_soffice():
    global _cache_soffice
    if _cache_soffice is not False:
        return _cache_soffice
    base = dossier_application()
    candidats = [
        base / "LibreOfficePortable" / "App" / "libreoffice" / "program" / "soffice.exe",
        base / "LibreOfficePortable" / "program" / "soffice.exe",
        base / "LibreOffice" / "program" / "soffice.exe",
        base / "libreoffice" / "program" / "soffice.exe",
    ]
    try:
        candidats.extend(base.glob("**/program/soffice.exe"))
    except OSError:
        pass
    vus = set()
    for c in candidats:
        s = str(c)
        if s in vus:
            continue
        vus.add(s)
        if Path(c).is_file():
            _cache_soffice = s
            return s
    for c in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ):
        if os.path.isfile(c):
            _cache_soffice = c
            return c
    for nom in ("soffice", "libreoffice"):
        found = shutil.which(nom)
        if found:
            _cache_soffice = found
            return found
    _cache_soffice = None
    return None

def convertir_via_word(source: Path, dest: Path) -> None:
    src = str(source.resolve()).replace("'", "''")
    dst = str(dest.resolve()).replace("'", "''")
    ps = (
        "$ErrorActionPreference = 'Stop'; "
        f"$src = '{src}'; $dst = '{dst}'; "
        "$w = New-Object -ComObject Word.Application; "
        "$w.Visible = $false; $w.DisplayAlerts = 0; "
        "try { $d = $w.Documents.Open($src, $false, $true); "
        "$d.SaveAs([ref]$dst, [ref]17); $d.Close($false); } "
        "finally { $w.Quit() }"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0 or not dest.is_file():
        err = (proc.stderr or proc.stdout or "Word n'a pas produit le PDF").strip()
        raise RuntimeError(err[:400])
