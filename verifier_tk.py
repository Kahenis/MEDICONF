# -*- coding: utf-8 -*-
"""Vérifie Tcl/Tk avant la compilation, puis dans le dossier compilé."""
import os
import shutil
import sys
import tkinter
from pathlib import Path

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


def avant():
    tcl = premier(candidats_tcl, "init.tcl")
    tk = premier(candidats_tk, "tk.tcl")
    print("AVANT compilation")
    print(" init.tcl :", tcl)
    print(" tk.tcl   :", tk)
    if tcl is None or tk is None:
        print("ERREUR : Tcl/Tk introuvable, compilation annulée.")
        sys.exit(1)
    print("Tcl/Tk source OK")


def poser(source, cible):
    if cible.exists():
        shutil.rmtree(cible)
    shutil.copytree(source, cible)
    print("copie", source, "->", cible)


def apres():
    dest = Path("dist/MEDICONF/_internal")
    if not dest.is_dir():
        print("ERREUR : dist/MEDICONF/_internal absent")
        sys.exit(1)
    tcl = premier(candidats_tcl, "init.tcl")
    tk = premier(candidats_tk, "tk.tcl")
    if tcl is None or tk is None:
        print("ERREUR : sources Tcl/Tk perdues après compilation")
        sys.exit(1)
    poser(tcl, dest / "_tcl_data")
    poser(tk, dest / "_tk_data")
    init_tcl = dest / "_tcl_data" / "init.tcl"
    tk_tcl = dest / "_tk_data" / "tk.tcl"
    print("APRES compilation")
    print(" init.tcl :", init_tcl, init_tcl.is_file())
    print(" tk.tcl   :", tk_tcl, tk_tcl.is_file())
    if not init_tcl.is_file() or not tk_tcl.is_file():
        print("ERREUR : dossiers _tcl_data ou _tk_data incomplets, zip annulé.")
        sys.exit(1)
    print("Tcl/Tk embarqué OK")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--apres"
    if mode == "--avant":
        avant()
    else:
        apres()
