# -*- coding: utf-8 -*-
from __future__ import annotations
import ctypes, os
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox
from conversion import est_document, est_image, est_pdf
from explorateur import choisir_type_source

_dernier = {"valeur": ""}
BFFM_SELCHANGED = 2

class _BROWSEINFO(ctypes.Structure):
    _fields_ = [("hwndOwner", wintypes.HWND), ("pidlRoot", ctypes.c_void_p), ("pszDisplayName", ctypes.c_wchar_p), ("lpszTitle", ctypes.c_wchar_p), ("ulFlags", wintypes.UINT), ("lpfn", ctypes.c_void_p), ("lParam", ctypes.c_long), ("iImage", ctypes.c_int)]

_CB = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)

@_CB
def _rappel(hwnd, msg, lp, _data):
    if msg == BFFM_SELCHANGED and lp:
        buf = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.shell32.SHGetPathFromIDListW(lp, buf) and buf.value:
            _dernier["valeur"] = buf.value
    return 0

def dialogue_avec_fichiers(titre: str) -> str:
    if os.name != "nt":
        return filedialog.askdirectory(title=titre) or ""
    _dernier["valeur"] = ""
    display = ctypes.create_unicode_buffer(260)
    bi = _BROWSEINFO()
    bi.pszDisplayName = ctypes.cast(display, ctypes.c_wchar_p)
    bi.lpszTitle = titre
    bi.ulFlags = 0x0040 | 0x0010 | 0x4000 | 0x8000 | 0x0050
    bi.lpfn = ctypes.cast(_rappel, ctypes.c_void_p)
    ctypes.windll.ole32.CoInitialize(None)
    pidl = ctypes.windll.shell32.SHBrowseForFolderW(ctypes.byref(bi))
    if not pidl:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    ok = ctypes.windll.shell32.SHGetPathFromIDListW(pidl, buf)
    ctypes.windll.ole32.CoTaskMemFree(pidl)
    return buf.value if ok and buf.value else _dernier["valeur"]

def _enregistrer_cible(fen, chemin: str) -> bool:
    chemin = (chemin or "").strip()
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
    return True

def appliquer(cls):
    def _parcourir_cible(self):
        d = dialogue_avec_fichiers("Choisir le dossier cible, fichiers visibles")
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
            f = filedialog.askopenfilename(parent=self, title="Choisir un fichier source", filetypes=[("Tous les fichiers", "*.*"), ("PDF", "*.pdf"), ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tif;*.tiff;*.webp"), ("Documents", "*.txt;*.rtf;*.doc;*.docx;*.odt")])
            if f:
                self._charger_source(Path(f))
    def _choisir_dossier_source(self):
        d = dialogue_avec_fichiers("Selectionner le dossier source, fichiers visibles")
        if not d:
            return
        p = Path(d)
        if p.is_file():
            p = p.parent
        self._charger_source(p)
    def _visible(self):
        voir_img = bool(self.filtre_images.get())
        voir_doc = bool(self.filtre_docs.get())
        out = []
        for p in self.fichiers:
            if est_pdf(p):
                out.append(p)
            elif est_image(p):
                if voir_img:
                    out.append(p)
            elif est_document(p):
                if voir_doc:
                    out.append(p)
        return out
    def _rafraichir_liste(self):
        self.zone_drop.delete(0, "end")
        for p in self._visible():
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
    cls._rafraichir_liste = _rafraichir_liste
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
    def relier(w):
        for enfant in w.winfo_children():
            try: txt = str(enfant.cget("text"))
            except Exception: txt = ""
            if txt in ("Images", "Documents"):
                enfant.configure(command=fen._rafraichir_liste)
            if enfant.winfo_class() in ("TEntry", "Entry"):
                enfant.bind("<FocusOut>", lambda _e: _enregistrer_cible(fen, fen.var_cible.get()), add="+")
                enfant.bind("<Return>", lambda _e: _enregistrer_cible(fen, fen.var_cible.get()), add="+")
            relier(enfant)
    fen.after(200, lambda: relier(fen))
