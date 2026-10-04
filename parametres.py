# -*- coding: utf-8 -*-
"""Paramètres dans le dossier AppData de l'utilisateur."""
from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def fichier_config() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if not base:
        base = str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "MEDICONF" / "parametres.json"


@dataclass
class Parametres:
    dossier_cible: str = ""
    parcourir_sous_dossiers: bool = False
    compression: bool = True
    qualite_compression: int = 75
    conserver_arborescence: bool = False
    conflit: str = "renommer"
    theme: str = "basic"

    def sauvegarder(self) -> None:
        chemin = fichier_config()
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def charger(cls) -> "Parametres":
        chemin = fichier_config()
        if not chemin.is_file():
            return cls()
        try:
            data = json.loads(chemin.read_text(encoding="utf-8-sig"))
        except Exception:
            return cls()
        valides = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valides)
