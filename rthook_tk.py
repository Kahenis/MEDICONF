# -*- coding: utf-8 -*-
"""Désigne les dossiers Tcl et Tk embarqués avant l'ouverture de l'interface."""
import os
import sys
from pathlib import Path


def _dossier(marque, noms):
    racines = [Path(getattr(sys, "_MEIPASS", "")), Path(sys.executable).resolve().parent]
    racines.append(racines[-1] / "_internal")
    for racine in racines:
        if not racine or not racine.exists():
            continue
        for nom in noms:
            candidat = racine / nom / marque
            if candidat.is_file():
                return str(candidat.parent)
        try:
            for fichier in racine.rglob(marque):
                return str(fichier.parent)
        except OSError:
            continue
    return ""


tcl = _dossier("init.tcl", ("_tcl_data", "tcl8.6", "lib/tcl8.6"))
tk = _dossier("tk.tcl", ("_tk_data", "tk8.6", "lib/tk8.6"))
if tcl:
    os.environ["TCL_LIBRARY"] = tcl
if tk:
    os.environ["TK_LIBRARY"] = tk
