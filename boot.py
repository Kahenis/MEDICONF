# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path


def _fixer_tcl() -> None:
    """Désigne les dossiers embarqués, même si une valeur incorrecte est déjà posée."""
    if not getattr(sys, "frozen", False):
        return
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    racines = [base, Path(sys.executable).resolve().parent, base / "_internal"]
    for racine in racines:
        for nom in ("_tcl_data", "tcl8.6"):
            if (racine / nom / "init.tcl").is_file():
                os.environ["TCL_LIBRARY"] = str(racine / nom)
                break
        for nom in ("_tk_data", "tk8.6"):
            if (racine / nom / "tk.tcl").is_file():
                os.environ["TK_LIBRARY"] = str(racine / nom)
                break


_fixer_tcl()

import conversion

_ancien = conversion.trouver_soffice

def _trouver_soffice():
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidats = [
        base / "LibreOfficePortable" / "App" / "libreoffice" / "program" / "soffice.exe",
        base / "LibreOfficePortable" / "program" / "soffice.exe",
    ]
    try:
        candidats.extend(base.glob("LibreOfficePortable/**/program/soffice.exe"))
    except OSError:
        pass
    for c in candidats:
        if c.is_file():
            return str(c)
    return _ancien()

conversion.trouver_soffice = _trouver_soffice

from menu import MenuDemarrage

if __name__ == "__main__":
    MenuDemarrage().mainloop()


_ancien = conversion.trouver_soffice

def _trouver_soffice():
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidats = [
        base / "LibreOfficePortable" / "App" / "libreoffice" / "program" / "soffice.exe",
        base / "LibreOfficePortable" / "program" / "soffice.exe",
    ]
    try:
        candidats.extend(base.glob("LibreOfficePortable/**/program/soffice.exe"))
    except OSError:
        pass
    for c in candidats:
        if c.is_file():
            return str(c)
    return _ancien()

conversion.trouver_soffice = _trouver_soffice

from menu import MenuDemarrage

if __name__ == "__main__":
    MenuDemarrage().mainloop()
