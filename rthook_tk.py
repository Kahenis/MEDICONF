# -*- coding: utf-8 -*-
"""Désigne Tcl/Tk avant l'interface, sans planter si le dossier a un autre nom."""
import os
import sys
from pathlib import Path


def _poser(marque, variable):
    if os.environ.get(variable):
        return
    racines = [Path(getattr(sys, "_MEIPASS", ""))]
    racines.append(Path(sys.executable).resolve().parent)
    racines.append(racines[-1] / "_internal")
    for racine in racines:
        if not racine or not racine.exists():
            continue
        try:
            for fichier in racine.rglob(marque):
                os.environ[variable] = str(fichier.parent)
                return
        except OSError:
            continue


_poser("init.tcl", "TCL_LIBRARY")
_poser("tk.tcl", "TK_LIBRARY")
