# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from tkinter import filedialog, messagebox
from conversion import est_document, est_image, est_pdf
from explorateur import choisir_type_source, explorer_dossier

APP = "MEDICONF \u2014 Convertisseur PDF"

def appliquer(cls) -> None:
    def _parcourir_cible(self) -> None:
        d = explorer_dossier(self, "Choisir le dossier cible")
        if d:
            self.var_cible.set(d)

    def _parcourir_source(self) -> None:
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            types = [
                ("Fichiers convertibles et PDF",
                 "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp *.ico *.jfif *.txt *.rtf *.doc *.docx *.odt *.pdf"),
                ("Tous", "*.*"),
            ]
            f = filedialog.askopenfilename(title="Choisir un fichier source", filetypes=types)
            if f:
                self._charger_source(Path(f))

    def _choisir_dossier_source(self) -> None:
        d = explorer_dossier(self, "Selectionner ce dossier source")
        if d:
            self._charger_source(Path(d))

    def _visible(self):
        out = []
        for p in self.fichiers:
            if est_pdf(p):
                out.append(p)
                continue
            if est_image(p) and not self.filtre_images.get():
                continue
            if est_document(p) and not self.filtre_docs.get():
                continue
            out.append(p)
        return out

    _ancien_libelle = cls._libelle

    def _libelle(self, p: Path) -> str:
        nom = _ancien_libelle(self, p)
        if est_pdf(p) and "copie seule" not in nom:
            nom += "  (copie seule)"
        return nom

    _ancien_charger = cls._charger_source

    def _charger_source(self, path: Path) -> None:
        path = Path(path)
        if path.is_file() and est_pdf(path):
            self.source_path = path
            self.lbl_source.configure(text=f"{path.parent}   --   {path.name}")
            self.fichiers = [path]
            self._rafraichir_liste()
            if messagebox.askyesno(APP, f"Copier ce PDF vers le dossier cible ?\n\n{path.name}"):
                self._convertir_un_fichier(path)
            return
        _ancien_charger(self, path)

    cls._parcourir_cible = _parcourir_cible
    cls._parcourir_source = _parcourir_source
    cls._choisir_dossier_source = _choisir_dossier_source
    cls._visible = _visible
    cls._libelle = _libelle
    cls._charger_source = _charger_source
