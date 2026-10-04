# -*- coding: utf-8 -*-
"""Scan du dossier source. Isolé pour ne pas dépendre des autres correctifs."""
from __future__ import annotations

import os
from pathlib import Path

from apercu import est_convertible


def lister(racine: Path, sous_dossiers: bool) -> list[Path]:
    racine = Path(racine)
    fichiers: list[Path] = []
    if sous_dossiers:
        for dirpath, _dirs, names in os.walk(racine):
            for nom in names:
                p = Path(dirpath) / nom
                if est_convertible(p):
                    fichiers.append(p)
    else:
        try:
            enfants = list(racine.iterdir())
        except OSError:
            enfants = []
        for enfant in enfants:
            if est_convertible(enfant):
                fichiers.append(enfant)
    fichiers.sort(key=lambda p: str(p).lower())
    return fichiers
