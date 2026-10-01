# -*- coding: utf-8 -*-
from pathlib import Path
import sys
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
