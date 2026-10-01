# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from conversion import est_document, est_image, est_pdf
from explorateur import choisir_type_source

def appliquer(cls):
    def _parcourir_cible(self):
        initial = self.var_cible.get().strip()
        d = filedialog.askdirectory(parent=self, title="Choisir le dossier cible", initialdir=initial if initial and Path(initial).is_dir() else str(Path.home()))
        if d:
            self.var_cible.set(d)
            self._sauver_params()
    def _parcourir_source(self):
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            f = filedialog.askopenfilename(parent=self, title="Choisir un fichier source", filetypes=[("Tous les fichiers", "*.*"), ("PDF", "*.pdf"), ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tif;*.tiff;*.webp"), ("Documents", "*.txt;*.rtf;*.doc;*.docx;*.odt")])
            if f:
                self._charger_source(Path(f))
    def _choisir_dossier_source(self):
        tape = self.var_source_saisie.get().strip() if getattr(self, "var_source_saisie", None) is not None else ""
        if tape:
            p = Path(tape)
            if p.is_file():
                p = p.parent
            if not p.exists():
                messagebox.showerror("MEDICONF", f"Chemin introuvable :\n{tape}", parent=self)
                return
            self._charger_source(p)
            return
        d = filedialog.askdirectory(parent=self, title="Selectionner le dossier source")
        if d:
            self.var_source_saisie.set(d)
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
        if not path.exists():
            messagebox.showerror("MEDICONF", f"Chemin introuvable :\n{path}", parent=self)
            return
        if path.is_file() and est_pdf(path):
            self.source_path = path
            self.lbl_source.configure(text=f"{path.parent}   --   {path.name}")
            self.fichiers = [path]
            self._rafraichir_liste()
            self._afficher_apercu(path)
            if messagebox.askyesno("MEDICONF", f"Copier ce PDF ?\n\n{path.name}", parent=self):
                self._convertir_un_fichier(path)
            return
        ancien_c(self, path)
        if getattr(self, "var_source_saisie", None) is not None and self.source_path:
            self.var_source_saisie.set(str(self.source_path))
    def _afficher_apercu(self, path):
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text=path.name)
        self.canvas_apercu.update_idletasks()
        cw = max(self.canvas_apercu.winfo_width(), 220)
        ch = max(self.canvas_apercu.winfo_height(), 220)
        try:
            from PIL import Image, ImageTk
            im = None
            if est_image(path):
                im = Image.open(path)
            elif path.suffix.lower() == ".pdf":
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(str(path))
                page = doc[0]
                im = page.render(scale=1.4).to_pil()
                page.close(); doc.close()
            if im is not None:
                im.thumbnail((cw - 16, ch - 16))
                self.apercu_img = ImageTk.PhotoImage(im)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
                return
        except Exception as e:
            self.canvas_apercu.create_text(cw // 2, ch // 2, text=str(e), fill="#444")
            return
    def _sauver_params(self):
        try:
            self.params.dossier_cible = self.var_cible.get().strip()
            self.params.parcourir_sous_dossiers = self.var_sous.get()
            self.params.compression = self.var_comp.get()
            self.params.qualite_compression = int(float(self.scale_qualite.get()))
            self.params.conserver_arborescence = self.var_arbo.get()
            self.params.conflit = self.var_conflit.get()
            self.params.sauvegarder()
        except Exception:
            pass
    def _quitter(self):
        _sauver_params(self)
        menu = getattr(self, "_menu_principal", None)
        try:
            self.destroy()
        except Exception:
            pass
        if menu is not None:
            try:
                menu.deiconify(); menu.lift(); menu.focus_force(); return
            except Exception:
                pass
        os._exit(0)
    cls._parcourir_cible = _parcourir_cible
    cls._parcourir_source = _parcourir_source
    cls._choisir_dossier_source = _choisir_dossier_source
    cls._visible = _visible
    cls._libelle = _libelle
    cls._charger_source = _charger_source
    cls._afficher_apercu = _afficher_apercu
    cls._sauver_params = _sauver_params
    cls._quitter = _quitter

def brancher(fen, menu):
    import tkinter as tk
    fen._menu_principal = menu
    barre = tk.Frame(fen, bg="#f4f6f8")
    barre.place(x=8, y=36, relwidth=1.0, height=32)
    tk.Label(barre, text="Dossier ou fichier source :", bg="#f4f6f8").pack(side="left")
    fen.var_source_saisie = tk.StringVar()
    tk.Entry(barre, textvariable=fen.var_source_saisie).pack(side="left", fill="x", expand=True, padx=6)
    tk.Button(barre, text="Utiliser ce chemin", command=fen._choisir_dossier_source).pack(side="left", padx=4)
    tk.Button(barre, text="Retour au menu", command=fen._quitter).pack(side="right", padx=8)
    try:
        fen.var_cible.trace_add("write", lambda *_: fen._sauver_params())
    except Exception:
        pass
    fen.protocol("WM_DELETE_WINDOW", fen._quitter)
