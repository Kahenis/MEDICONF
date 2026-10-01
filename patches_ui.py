# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from pathlib import Path
from tkinter import filedialog, messagebox
from conversion import est_document, est_image, est_pdf
from explorateur import choisir_type_source

def _enregistrer_cible(fen, chemin: str) -> bool:
    chemin = (chemin or "").strip()
    if not chemin:
        return False
    p = Path(chemin)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        messagebox.showerror("MEDICONF", f"Dossier cible impossible :\n{e}", parent=fen)
        return False
    if fen.var_cible.get() != str(p):
        fen.var_cible.set(str(p))
    fen.params.dossier_cible = str(p)
    try:
        fen.params.parcourir_sous_dossiers = fen.var_sous.get()
        fen.params.compression = fen.var_comp.get()
        fen.params.qualite_compression = int(float(fen.scale_qualite.get()))
        fen.params.conserver_arborescence = fen.var_arbo.get()
        fen.params.conflit = fen.var_conflit.get()
    except Exception:
        pass
    fen.params.sauvegarder()
    if getattr(fen, "lbl_cible_etat", None) is not None:
        fen.lbl_cible_etat.configure(text=f"Dossier cible enregistre : {p}")
    return True

def appliquer(cls):
    def _parcourir_cible(self):
        initial = self.var_cible.get().strip()
        d = filedialog.askdirectory(parent=self, title="Choisir le dossier cible", initialdir=initial if initial and Path(initial).is_dir() else str(Path.home()))
        if d:
            _enregistrer_cible(self, d)
    def _valider_cible(self):
        d = self.var_cible.get().strip()
        if not d:
            messagebox.showwarning("MEDICONF", "Indiquez un dossier cible.", parent=self)
            return
        if _enregistrer_cible(self, d):
            messagebox.showinfo("MEDICONF", f"Dossier cible enregistre :\n{d}", parent=self)
    def _parcourir_source(self):
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            f = filedialog.askopenfilename(parent=self, title="Choisir un fichier source", filetypes=[("Tous les fichiers", "*.*"), ("PDF", "*.pdf"), ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tif;*.tiff;*.webp"), ("Documents", "*.txt;*.rtf;*.doc;*.docx;*.odt")])
            if f:
                self._charger_source(Path(f))
    def _choisir_dossier_source(self):
        d = filedialog.askdirectory(parent=self, title="Selectionner le dossier source")
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
    def _sauver_params(self):
        _enregistrer_cible(self, self.var_cible.get())
    def _quitter(self):
        _enregistrer_cible(self, self.var_cible.get())
        menu = getattr(self, "_menu_principal", None)
        try: self.destroy()
        except Exception: pass
        if menu is not None:
            try:
                menu.deiconify(); menu.lift(); return
            except Exception:
                pass
        os._exit(0)
    cls._parcourir_cible = _parcourir_cible
    cls._valider_cible = _valider_cible
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
    tk.Button(fen, text="Retour au menu", command=fen._quitter).place(relx=1.0, rely=0.0, x=-10, y=6, anchor="ne")
    fen.protocol("WM_DELETE_WINDOW", fen._quitter)
    fen.lbl_cible_etat = tk.Label(fen, text="", bg="#f4f6f8", fg="#1f4e79")
    fen.lbl_cible_etat.place(x=12, y=8)
    if fen.params.dossier_cible:
        fen.lbl_cible_etat.configure(text=f"Dossier cible : {fen.params.dossier_cible}")
    def lier(w):
        for enfant in w.winfo_children():
            if enfant.winfo_class() in ("TEntry", "Entry"):
                enfant.bind("<FocusOut>", lambda _e: _enregistrer_cible(fen, fen.var_cible.get()), add="+")
                enfant.bind("<Return>", lambda _e: _enregistrer_cible(fen, fen.var_cible.get()), add="+")
            lier(enfant)
    fen.after(300, lambda: lier(fen))
