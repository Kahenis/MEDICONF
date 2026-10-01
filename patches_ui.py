# -*- coding: utf-8 -*-
from __future__ import annotations
import os, zipfile
from pathlib import Path
from tkinter import filedialog, messagebox
from xml.etree import ElementTree
from conversion import est_document, est_image, est_pdf, ressource_ok
from explorateur import choisir_type_source

def _dossier(titre):
    return filedialog.askdirectory(title=titre) or ""

def _enregistrer_cible(fen, chemin):
    chemin = (chemin or "").strip().strip('"')
    if not chemin:
        return False
    p = Path(chemin)
    if p.is_file():
        p = p.parent
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        messagebox.showerror("MEDICONF", f"Dossier cible impossible :\n{e}", parent=fen)
        return False
    fen.var_cible.set(str(p))
    fen.params.dossier_cible = str(p)
    try:
        fen.params.parcourir_sous_dossiers = bool(fen.var_sous.get())
        fen.params.compression = bool(fen.var_comp.get())
        fen.params.qualite_compression = int(float(fen.var_qualite.get()))
        fen.params.conserver_arborescence = bool(fen.var_arbo.get())
        fen.params.conflit = fen.var_conflit.get()
    except Exception:
        pass
    fen.params.sauvegarder()
    return True

def _texte_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    textes = [n.text for n in root.iter() if n.tag.endswith("}t") and n.text]
    return "\n".join(textes)[:4000] or "(document vide)"

def appliquer(cls):
    def _parcourir_cible(self):
        d = _dossier("Choisir le dossier cible")
        if d:
            _enregistrer_cible(self, d)
    def _valider_cible(self):
        if _enregistrer_cible(self, self.var_cible.get()):
            messagebox.showinfo("MEDICONF", f"Dossier cible enregistre :\n{self.var_cible.get()}", parent=self)
    def _parcourir_source(self):
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            f = filedialog.askopenfilename(title="Choisir un fichier source", filetypes=[("Tous les fichiers", "*.*"), ("PDF", "*.pdf"), ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tif;*.tiff;*.webp"), ("Documents", "*.txt;*.rtf;*.doc;*.docx;*.odt")])
            if f:
                self._charger_source(Path(f))
    def _choisir_dossier_source(self):
        d = _dossier("Selectionner le dossier source")
        if d:
            self._charger_source(Path(d))
    def _scanner(self, racine):
        fichiers = []
        racine = Path(racine)
        if self.var_sous.get():
            for dirpath, _dirs, names in os.walk(racine):
                for n in names:
                    p = Path(dirpath) / n
                    if ressource_ok(p):
                        fichiers.append(p)
        else:
            for p in racine.iterdir():
                if p.is_file() and ressource_ok(p):
                    fichiers.append(p)
        fichiers.sort(key=lambda x: str(x).lower())
        return fichiers
    def _sauver_et_rescan(self):
        try:
            self.params.parcourir_sous_dossiers = bool(self.var_sous.get())
            self.params.sauvegarder()
        except Exception:
            pass
        if getattr(self, "source_path", None) and Path(self.source_path).is_dir():
            self.fichiers = self._scanner(self.source_path)
            self._rafraichir_liste()
    def _visible(self):
        voir_img = bool(self.filtre_images.get())
        voir_doc = bool(self.filtre_docs.get())
        out = []
        for p in self.fichiers:
            if est_pdf(p):
                out.append(p)
            elif est_image(p) and voir_img:
                out.append(p)
            elif est_document(p) and voir_doc:
                out.append(p)
        return out
    def _rafraichir_liste(self):
        self.zone_drop.delete(0, "end")
        self._index_visible = self._visible()
        for p in self._index_visible:
            key = str(p)
            if key not in self.vars_coche:
                self.vars_coche[key] = True
            marque = "\u2611" if self.vars_coche.get(key, True) else "\u2610"
            self.zone_drop.insert("end", f" {marque}  {self._libelle(p)}")
    ancien = cls._libelle
    def _libelle(self, p):
        nom = ancien(self, p)
        if est_pdf(p) and "copie seule" not in nom:
            nom += "  (copie seule)"
        return nom
    def _clic_liste(self, evt):
        fichiers = getattr(self, "_index_visible", None) or self._visible()
        idx = self.zone_drop.nearest(evt.y)
        if idx < 0 or idx >= len(fichiers):
            return
        p = fichiers[idx]
        if evt.x < 28:
            key = str(p)
            self.vars_coche[key] = not self.vars_coche.get(key, True)
            self._rafraichir_liste()
            return
        self.zone_drop.selection_clear(0, "end")
        self.zone_drop.selection_set(idx)
        self._afficher_apercu(p)
    def _afficher_apercu(self, path):
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text=path.name)
        self.canvas_apercu.update_idletasks()
        cw = max(self.canvas_apercu.winfo_width(), 240)
        ch = max(self.canvas_apercu.winfo_height(), 240)
        try:
            from PIL import Image, ImageTk
            im = None
            if est_image(path):
                im = Image.open(path)
            elif path.suffix.lower() == ".pdf":
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(str(path))
                page = doc[0]
                im = page.render(scale=1.3).to_pil()
                page.close(); doc.close()
            if im is not None:
                im.thumbnail((cw - 12, ch - 12))
                self.apercu_img = ImageTk.PhotoImage(im)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
                return
            if path.suffix.lower() == ".docx":
                self.canvas_apercu.create_text(12, 12, anchor="nw", width=cw - 24, text=_texte_docx(path), fill="#222")
                return
            if path.suffix.lower() in {".txt", ".rtf"}:
                self.canvas_apercu.create_text(12, 12, anchor="nw", width=cw - 24, text=path.read_text(encoding="utf-8", errors="ignore")[:4000], fill="#222")
                return
        except Exception as e:
            self.canvas_apercu.create_text(cw // 2, ch // 2, text=f"Apercu impossible\n{e}", fill="#444")
            return
        self.canvas_apercu.create_text(20, 20, anchor="nw", text=path.name, fill="#222")
    def _sauver_params(self):
        if self.var_cible.get().strip():
            _enregistrer_cible(self, self.var_cible.get())
    def _quitter(self):
        if self.var_cible.get().strip():
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
    cls._scanner = _scanner
    cls._visible = _visible
    cls._rafraichir_liste = _rafraichir_liste
    cls._libelle = _libelle
    cls._clic_liste = _clic_liste
    cls._afficher_apercu = _afficher_apercu
    cls._sauver_params = _sauver_params
    cls._sauver_et_rescan = _sauver_et_rescan
    cls._quitter = _quitter

def brancher(fen, menu):
    import tkinter as tk
    fen._menu_principal = menu
    tk.Button(fen, text="Retour au menu", command=fen._quitter).place(relx=1.0, rely=0.0, x=-10, y=6, anchor="ne")
    fen.protocol("WM_DELETE_WINDOW", fen._quitter)
    fen.zone_drop.bind("<Button-1>", fen._clic_liste)
    def relier(w):
        for enfant in w.winfo_children():
            try: txt = str(enfant.cget("text"))
            except Exception: txt = ""
            if "sous-dossier" in txt.lower():
                enfant.configure(command=fen._sauver_et_rescan)
            if txt in ("Images", "Documents"):
                enfant.configure(command=fen._rafraichir_liste)
            relier(enfant)
    relier(fen)
