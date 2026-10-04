# -*- coding: utf-8 -*-
"""Le paquet ne doit plus contenir le contrôle qui plante au démarrage."""
import sys
from pathlib import Path

racine = Path("build")
trouves = []
for fichier in racine.rglob("*"):
    if not fichier.is_file():
        continue
    if fichier.suffix.lower() not in {".toc", ".html", ".txt", ".py", ""}:
        continue
    try:
        texte = fichier.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    if "pyi_rth_tkinter" in texte or "pyi_rth__tkinter" in texte:
        trouves.append(str(fichier))
if trouves:
    print("ERREUR : controle tkinter encore present")
    print("\n".join(trouves[:8]))
    sys.exit(1)
print("controle tkinter absent du build")
