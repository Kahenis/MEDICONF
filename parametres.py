# -*- coding: utf-8 -*-
"""Persistance des parametres."""
from __future__ import annotations
import json, os, sys
from dataclasses import asdict, dataclass
from pathlib import Path

def chemins_config() -> list[Path]:
    chemins = []
    if getattr(sys, "frozen", False):
        chemins.append(Path(sys.executable).resolve().parent / "parametres.json")
    else:
        chemins.append(Path(__file__).resolve().parent / "parametres.json")
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if base:
        chemins.append(Path(base) / "MEDICONF" / "parametres.json")
    else:
        chemins.append(Path.home() / ".mediconf" / "parametres.json")
    return chemins


def dossier_config() -> Path:
    return chemins_config()[0].parent

@dataclass
class Parametres:
    dossier_cible: str = ""
    parcourir_sous_dossiers: bool = False
    compression: bool = True
    qualite_compression: int = 75
    conserver_arborescence: bool = False
    conflit: str = "renommer"

    def sauvegarder(self) -> None:
        contenu = json.dumps(asdict(self), ensure_ascii=False, indent=2)
        for chemin in chemins_config():
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(contenu, encoding="utf-8")

    @classmethod
    def charger(cls) -> "Parametres":
        for chemin in chemins_config():
            if not chemin.is_file():
                continue
            try:
                data = json.loads(chemin.read_text(encoding="utf-8"))
                valides = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**valides)
            except Exception:
                continue
        return cls()
