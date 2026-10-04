# -*- coding: utf-8 -*-
"""Retire le contrôle PyInstaller qui exige _tk_data et plante au démarrage."""
from pathlib import Path

spec = Path("MEDICONF.spec")
texte = spec.read_text(encoding="utf-8")
texte = texte.replace("runtime_hooks=[]", "runtime_hooks=['rthook_tk.py']")
if "pyi_rth_tkinter" not in texte:
    texte = texte.replace(
        "a.scripts,",
        "[s for s in a.scripts if 'pyi_rth_tkinter' not in str(s)],",
        1,
    )
else:
    texte = texte.replace(
        "a.scripts,",
        "[s for s in a.scripts if 'pyi_rth_tkinter' not in str(s)],",
        1,
    )
spec.write_text(texte, encoding="utf-8")
print("controle _tk_data retire du lanceur")

