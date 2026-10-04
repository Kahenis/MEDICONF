# -*- coding: utf-8 -*-
"""Place Tcl/Tk exactement là où le lanceur PyInstaller les attend."""
import os
import shutil
import sys
import tkinter
from pathlib import Path

dest = Path("dist/MEDICONF/_internal")
if not dest.is_dir():
    print("dossier manquant", dest)
    sys.exit(1)

root = Path(getattr(sys, "base_prefix", sys.prefix))
candidats_tcl = [
    Path(os.environ.get("TCL_LIBRARY", "")),
    root / "tcl" / "tcl8.6",
    root / "lib" / "tcl8.6",
    Path(tkinter.__file__).resolve().parents[1] / "tcl" / "tcl8.6",
]
candidats_tk = [
    Path(os.environ.get("TK_LIBRARY", "")),
    root / "tcl" / "tk8.6",
    root / "lib" / "tk8.6",
    Path(tkinter.__file__).resolve().parents[1] / "tcl" / "tk8.6",
]

def premier(candidats, marqueur):
    for chemin in candidats:
        if chemin and (chemin / marqueur).is_file():
            return chemin
    return None

tcl = premier(candidats_tcl, "init.tcl")
tk = premier(candidats_tk, "tk.tcl")
print("tcl", tcl)
print("tk", tk)
if tcl is None or tk is None:
    sys.exit(1)

def poser(source, cible):
    if cible.exists():
        shutil.rmtree(cible)
    shutil.copytree(source, cible)
    print("copie", source, "->", cible)

poser(tcl, dest / "_tcl_data")
poser(tk, dest / "_tk_data")
if not (dest / "_tk_data" / "tk.tcl").is_file() or not (dest / "_tcl_data" / "init.tcl").is_file():
    sys.exit(1)
print("Tcl/Tk pret")
