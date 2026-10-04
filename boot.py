# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path


def _fixer_tcl() -> None:
    """Le build Windows ne trouve parfois pas tk.tcl. On le désigne avant Tk."""
    if not getattr(sys, "frozen", False):
        return
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    racines = [base, Path(sys.executable).resolve().parent, base / "_internal"]
    for racine in racines:
        if os.environ.get("TCL_LIBRARY"):
            break
        for candidat in racine.rglob("init.tcl"):
            os.environ["TCL_LIBRARY"] = str(candidat.parent)
            break
    for racine in racines:
        if os.environ.get("TK_LIBRARY"):
            break
        for candidat in racine.rglob("tk.tcl"):
            os.environ["TK_LIBRARY"] = str(candidat.parent)
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
