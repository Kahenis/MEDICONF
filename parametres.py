# -*- coding: utf-8 -*-
"""Persistance des parametres."""
from __future__ import annotations
import json, os
from dataclasses import asdict, dataclass
from pathlib import Path

def dossier_config() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if base:
        d = Path(base) / "ConvertisseurPDF"
    else:
        d = Path.home() / ".convertisseur_pdf"
    d.mkdir(parents=True, exist_ok=True)
    return d

FICHIER_CONFIG = dossier_config() / "parametres.json"

@dataclass
class Parametres:
    dossier_cible: str = ""
    parcourir_sous_dossiers: bool = False
    compression: bool = True
    qualite_compression: int = 75
    conserver_arborescence: bool = False
    conflit: str = "renommer"

    def sauvegarder(self) -> None:
        FICHIER_CONFIG.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def charger(cls) -> "Parametres":
        if not FICHIER_CONFIG.exists():
            return cls()
        try:
            data = json.loads(FICHIER_CONFIG.read_text(encoding="utf-8"))
            valides = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**valides)
        except Exception:
            return cls()
