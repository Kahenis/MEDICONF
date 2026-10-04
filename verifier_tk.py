# -*- coding: utf-8 -*-
"""Vérifie que tk.tcl est dans le dossier compilé, sinon le copie."""
import os
import shutil
import sys
import tkinter
from pathlib import Path

dest = Path("dist/MEDICONF/_internal")
if not dest.is_dir():
    print("dossier manquant", dest)
    sys.exit(1)

root = Path(tkinter.__file__).resolve().parents[1]
tcl = Path(os.environ.get("TCL_LIBRARY") or root / "tcl" / "tcl8.6")
tk = Path(os.environ.get("TK_LIBRARY") or root / "tcl" / "tk8.6")
print("tcl", tcl, tcl.exists())
print("tk", tk, tk.exists())
if not any(dest.rglob("tk.tcl")) and (tk / "tk.tcl").is_file():
    shutil.copytree(tk, dest / "_tk_data", dirs_exist_ok=True)
if not any(dest.rglob("init.tcl")) and (tcl / "init.tcl").is_file():
    shutil.copytree(tcl, dest / "_tcl_data", dirs_exist_ok=True)
trouves = list(dest.rglob("tk.tcl"))
print("tk.tcl", trouves[:3])
sys.exit(0 if trouves else 1)
