# -*- coding: utf-8 -*-
"""Retire le contrôle qui exige _tk_data et plante avant le programme."""
from pathlib import Path

spec = Path("MEDICONF.spec")
texte = spec.read_text(encoding="utf-8")
texte = texte.replace("runtime_hooks=[]", "runtime_hooks=['rthook_tk.py']")
ancien = texte
texte = texte.replace(
    "a.scripts,",
    "[s for s in a.scripts if 'pyi_rth' not in str(s) or 'tkinter' not in str(s)],",
)
if texte == ancien or "tkinter" not in texte.split("EXE(")[-1][:500]:
    raise SystemExit("le controle tkinter n'a pas ete retire du spec")
spec.write_text(texte, encoding="utf-8")
print("controle tkinter retire")
