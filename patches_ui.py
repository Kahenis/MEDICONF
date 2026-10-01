# -*- coding: utf-8 -*-
from __future__ import annotations
import ctypes, os
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from conversion import est_document, est_image, est_pdf
from explorateur import choisir_type_source

class _BROWSEINFO(ctypes.Structure):
    _fields_ = [("hwndOwner", wintypes.HWND), ("pidlRoot", ctypes.c_void_p), ("pszDisplayName", ctypes.c_wchar_p), ("lpszTitle", ctypes.c_wchar_p), ("ulFlags", wintypes.UINT), ("lpfn", ctypes.c_void_p), ("lParam", ctypes.c_long), ("iImage", ctypes.c_int)]

def dialogue_dossier(titre: str) -> str:
    if os.name != "nt":
        return filedialog.askdirectory(title=titre) or ""
    shell = ctypes.windll.shell32
    ole = ctypes.windll.ole32
    display = ctypes.create_unicode_buffer(260)
    bi = _BROWSEINFO()
    bi.pszDisplayName = ctypes.cast(display, ctypes.c_wchar_p)
    bi.lpszTitle = titre
    bi.ulFlags = 0x0001 | 0x0040 | 0x0010 | 0x4000 | 0x8000 | 0x0050
    ole.CoInitialize(None)
    pidl = shell.SHBrowseForFolderW(ctypes.byref(bi))
    if not pidl:
        return ""
    chemin = ctypes.create_unicode_buffer(1024)
    ok = shell.SHGetPathFromIDListW(pidl, chemin)
    ole.CoTaskMemFree(pidl)
    return chemin.value if ok else ""

def appliquer(cls) -> None:
    def _parcourir_cible(self):
        d = dialogue_dossier("Choisir le dossier cible")
        if d:
            if Path(d).is_file():
                d = str(Path(d).parent)
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
        d = dialogue_dossier("Selectionner le dossier source (fichiers visibles)")
        if not d:
            return
        p = Path(d)
        if p.is_file():
            p = p.parent
        self._charger_source(p)
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
            elif est_pdf(path):
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
            self.canvas_apercu.create_text(cw // 2, ch // 2, text=f"Apercu impossible\n{e}", fill="#444")
            return
        self.canvas_apercu.create_text(20, 20, anchor="nw", text=path.name, fill="#222")
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
        maitre = getattr(self, "master", None)
        try:
            self.destroy()
        except Exception:
            pass
        try:
            if maitre is not None:
                maitre.deiconify(); maitre.lift(); return
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

def brancher_memoire(fen):
    try:
        fen.var_cible.trace_add("write", lambda *_: fen._sauver_params())
    except Exception:
        pass
    ttk.Button(fen, text="Retour au menu", command=fen._quitter).place(relx=1.0, rely=0.0, x=-10, y=6, anchor="ne")
    fen.protocol("WM_DELETE_WINDOW", fen._quitter)
