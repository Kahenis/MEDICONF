# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from pathlib import Path
from tkinter import filedialog, messagebox
from conversion import est_document, est_image, est_pdf
from explorateur import choisir_type_source

def appliquer(cls) -> None:
    def _parcourir_cible(self) -> None:
        initial = self.var_cible.get().strip() or str(Path.home())
        d = filedialog.askdirectory(parent=self, title="Choisir le dossier cible", initialdir=initial if Path(initial).is_dir() else str(Path.home()))
        if d:
            self.var_cible.set(d)
    def _parcourir_source(self) -> None:
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            types = [("Fichiers convertibles et PDF", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp *.ico *.jfif *.txt *.rtf *.doc *.docx *.odt *.pdf"), ("Tous", "*.*")]
            f = filedialog.askopenfilename(parent=self, title="Choisir un fichier source", filetypes=types)
            if f:
                self._charger_source(Path(f))
    def _choisir_dossier_source(self) -> None:
        d = filedialog.askdirectory(parent=self, title="Selectionner ce dossier source")
        if d:
            self._charger_source(Path(d))
    def _visible(self):
        out = []
        for p in self.fichiers:
            if est_pdf(p):
                out.append(p); continue
            if est_image(p) and not self.filtre_images.get():
                continue
            if est_document(p) and not self.filtre_docs.get():
                continue
            out.append(p)
        return out
    ancien = cls._libelle
    def _libelle(self, p):
        nom = ancien(self, p)
        if est_pdf(p) and "copie seule" not in nom:
            nom += "  (copie seule)"
        return nom
    ancien_c = cls._charger_source
    def _charger_source(self, path):
        path = Path(path)
        if path.is_file() and est_pdf(path):
            self.source_path = path
            self.lbl_source.configure(text=f"{path.parent}   --   {path.name}")
            self.fichiers = [path]
            self._rafraichir_liste()
            if messagebox.askyesno("MEDICONF", f"Copier ce PDF vers le dossier cible ?\n\n{path.name}", parent=self):
                self._convertir_un_fichier(path)
            return
        ancien_c(self, path)
    def _quitter(self):
        try:
            self._sauver_params()
        except Exception:
            pass
        maitre = getattr(self, "master", None)
        self.destroy()
        try:
            if maitre is not None:
                maitre.deiconify()
                maitre.lift()
        except Exception:
            os._exit(0)
    cls._parcourir_cible = _parcourir_cible
    cls._parcourir_source = _parcourir_source
    cls._choisir_dossier_source = _choisir_dossier_source
    cls._visible = _visible
    cls._libelle = _libelle
    cls._charger_source = _charger_source
    cls._quitter = _quitter
