# -*- coding: utf-8 -*-
"""Zippe le dossier compilé et refuse le zip si tk.tcl ou init.tcl manque."""
import sys
import zipfile
from pathlib import Path

root = Path("dist/MEDICONF")
archive = Path("MEDICONF-windows.zip")
if not root.is_dir():
    print("dossier compile absent")
    sys.exit(1)

with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for fichier in root.rglob("*"):
        if fichier.is_file():
            z.write(fichier, Path("MEDICONF") / fichier.relative_to(root))

noms = zipfile.ZipFile(archive).namelist()
a_tk = any(n.replace("\\", "/") == "MEDICONF/_internal/_tk_data/tk.tcl" for n in noms)
a_tcl = any(n.replace("\\", "/") == "MEDICONF/_internal/_tcl_data/init.tcl" for n in noms)
print("chemin exige : MEDICONF/_internal/_tk_data/tk.tcl ->", a_tk)
print("chemin exige : MEDICONF/_internal/_tcl_data/init.tcl ->", a_tcl)
if not a_tk or not a_tcl:
    print("ERREUR : zip incomplet, non publie")
    sys.exit(1)
print("zip OK")
