# -*- coding: utf-8 -*-
"""Partie 1 : vrai chemin, sous-dossiers, dialogue avec fichiers, apercu."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox

from conversion import EXTENSIONS_OK, est_document, est_image, est_pdf
from explorateur import choisir_type_source

SIGDN_FILESYSPATH = 0x80058000
BFFM_SELCHANGED = 2
_dernier = {"chemin": ""}


def ressource_ok(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in EXTENSIONS_OK


def resoudre_chemin(chemin: str) -> str:
    brut = (chemin or "").strip().strip('"')
    if not brut:
        return ""
    p = Path(brut)
    if p.is_file():
        p = p.parent
    if p.exists():
        return str(p.resolve())
    connus = {
        "documents": Path.home() / "Documents",
        "mes documents": Path.home() / "Documents",
        "bureau": Path.home() / "Desktop",
        "desktop": Path.home() / "Desktop",
        "images": Path.home() / "Pictures",
        "photos": Path.home() / "Pictures",
        "telechargements": Path.home() / "Downloads",
        "téléchargements": Path.home() / "Downloads",
        "downloads": Path.home() / "Downloads",
        "musique": Path.home() / "Music",
        "videos": Path.home() / "Videos",
        "vidéos": Path.home() / "Videos",
    }
    cible = connus.get(p.name.lower())
    if cible and cible.exists():
        return str(cible.resolve())
    return str(p)


def _shell():
    shell = ctypes.windll.shell32
    shell.SHBrowseForFolderW.restype = ctypes.c_void_p
    shell.SHBrowseForFolderW.argtypes = [ctypes.c_void_p]
    shell.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    shell.SHGetPathFromIDListW.restype = wintypes.BOOL
    shell.SHGetNameFromIDList.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_wchar_p)]
    shell.SHGetNameFromIDList.restype = ctypes.c_long
    ole = ctypes.windll.ole32
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    return shell


def _chemin_pidl(pidl) -> str:
    if not pidl:
        return ""
    if not isinstance(pidl, int):
        pidl = ctypes.cast(pidl, ctypes.c_void_p).value or 0
    if not pidl:
        return ""
    shell = _shell()
    buf = ctypes.create_unicode_buffer(32768)
    if shell.SHGetPathFromIDListW(ctypes.c_void_p(pidl), buf) and buf.value:
        return buf.value
    ptr = ctypes.c_wchar_p()
    if shell.SHGetNameFromIDList(ctypes.c_void_p(pidl), SIGDN_FILESYSPATH, ctypes.byref(ptr)) == 0 and ptr.value:
        valeur = ptr.value
        ctypes.windll.ole32.CoTaskMemFree(ptr)
        return valeur
    return ""


class _BROWSEINFO(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND),
        ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", ctypes.c_wchar_p),
        ("lpszTitle", ctypes.c_wchar_p),
        ("ulFlags", wintypes.UINT),
        ("lpfn", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("iImage", ctypes.c_int),
    ]


_CB = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)


@_CB
def _rappel(_hwnd, msg, lp, _data):
    if msg == BFFM_SELCHANGED and lp:
        chemin = _chemin_pidl(lp)
        if chemin:
            _dernier["chemin"] = chemin
    return 0


def dialogue_dossier(titre: str) -> str:
    if os.name != "nt":
        return filedialog.askdirectory(title=titre) or ""
    _dernier["chemin"] = ""
    display = ctypes.create_unicode_buffer(520)
    bi = _BROWSEINFO()
    bi.pszDisplayName = ctypes.cast(display, ctypes.c_wchar_p)
    bi.lpszTitle = titre + " — dossiers et fichiers visibles."
    bi.ulFlags = 0x0040 | 0x0010 | 0x4000 | 0x8000
    bi.lpfn = ctypes.cast(_rappel, ctypes.c_void_p)
    ctypes.windll.ole32.CoInitialize(None)
    shell = _shell()
    pidl = shell.SHBrowseForFolderW(ctypes.byref(bi))
    chemin = ""
    if pidl:
        chemin = _chemin_pidl(pidl) or _dernier["chemin"]
        ctypes.windll.ole32.CoTaskMemFree(ctypes.c_void_p(pidl))
    else:
        return ""
    chemin = resoudre_chemin(chemin or _dernier["chemin"])
    if not chemin or not Path(chemin).exists():
        messagebox.showerror(
            "MEDICONF",
            "Le dossier a ete choisi mais Windows n'a pas renvoye son chemin.\n"
            f"Nom affiche : {display.value or '?'}\n\n"
            "Choisissez-le a nouveau dans le selecteur de secours.",
        )
        return filedialog.askdirectory(title=titre) or ""
    return chemin


def _enregistrer_cible(fen, chemin: str) -> bool:
    chemin = resoudre_chemin(chemin)
    if not chemin:
        return False
    p = Path(chemin)
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


def appliquer(cls) -> None:
    def _parcourir_cible(self) -> None:
        d = dialogue_dossier("Choisir le dossier cible")
        if d:
            _enregistrer_cible(self, d)

    def _valider_cible(self) -> None:
        if _enregistrer_cible(self, self.var_cible.get()):
            messagebox.showinfo("MEDICONF", f"Dossier cible enregistré :\n{self.var_cible.get()}", parent=self)

    def _parcourir_source(self) -> None:
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            f = filedialog.askopenfilename(
                title="Choisir un fichier source",
                filetypes=[("Tous les fichiers", "*.*"), ("PDF", "*.pdf"),
                           ("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tif;*.tiff;*.webp"),
                           ("Documents", "*.txt;*.rtf;*.doc;*.docx;*.odt")],
            )
            if f:
                self._charger_source(Path(f))

    def _choisir_dossier_source(self) -> None:
        d = dialogue_dossier("Sélectionner le dossier source")
        if d:
            self._charger_source(Path(d))

    def _scanner(self, racine: Path):
        fichiers = []
        racine = Path(resoudre_chemin(str(racine)))
        if bool(self.var_sous.get()):
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

    def _sauver_et_rescan(self) -> None:
        try:
            self.params.parcourir_sous_dossiers = bool(self.var_sous.get())
            self.params.sauvegarder()
        except Exception:
            pass
        if getattr(self, "source_path", None) and Path(self.source_path).is_dir():
            self.fichiers = self._scanner(self.source_path)
            self._rafraichir_liste()
            self._log(f"{len(self.fichiers)} fichier(s) — sous-dossiers : {'oui' if self.var_sous.get() else 'non'}")

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

    def _rafraichir_liste(self) -> None:
        self.zone_drop.delete(0, "end")
        self._index_visible = self._visible()
        for p in self._index_visible:
            key = str(p)
            if key not in self.vars_coche:
                self.vars_coche[key] = True
            marque = "\u2611" if self.vars_coche.get(key, True) else "\u2610"
            self.zone_drop.insert("end", f" {marque}  {self._libelle(p)}")

    ancien = cls._libelle

    def _libelle(self, p: Path) -> str:
        nom = ancien(self, p)
        if est_pdf(p) and "copie seule" not in nom:
            nom += "  (copie seule)"
        return nom

    def _clic_liste(self, evt):
        fichiers = getattr(self, "_index_visible", None) or self._visible()
        idx = self.zone_drop.nearest(evt.y)
        if idx < 0 or idx >= len(fichiers):
            return "break"
        p = fichiers[idx]
        if evt.x < 28:
            self.vars_coche[str(p)] = not self.vars_coche.get(str(p), True)
            self._rafraichir_liste()
            return "break"
        self.zone_drop.selection_clear(0, "end")
        self.zone_drop.selection_set(idx)
        self.after(30, lambda chemin=p: self._afficher_apercu(chemin))
        return "break"

    def _afficher_apercu(self, path: Path) -> None:
        path = Path(path)
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text=str(path))
        self.canvas_apercu.update_idletasks()
        cw = max(self.canvas_apercu.winfo_width(), 360)
        ch = max(self.canvas_apercu.winfo_height(), 280)
        try:
            from PIL import Image, ImageTk
            im = None
            if est_image(path):
                im = Image.open(path)
                im.load()
            elif path.suffix.lower() == ".pdf":
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(str(path))
                page = doc[0]
                im = page.render(scale=1.5).to_pil()
                page.close()
                doc.close()
            if im is not None:
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGB")
                im.thumbnail((cw - 8, ch - 8))
                self.apercu_img = ImageTk.PhotoImage(im)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
                return
        except Exception as e:
            self.canvas_apercu.create_text(cw // 2, ch // 2, text=f"Aperçu impossible\n{e}", fill="#444")
            return
        self.canvas_apercu.create_text(16, 16, anchor="nw", text=path.name, fill="#222")

    def _charger_source(self, path: Path) -> None:
        path = Path(resoudre_chemin(str(path)) if not Path(path).is_file() else path)
        if not path.exists():
            messagebox.showerror("MEDICONF", f"Chemin introuvable :\n{path}", parent=self)
            return
        self.source_path = path
        if path.is_file():
            self.lbl_source.configure(text=f"{path.parent}   —   {path.name}")
            self.fichiers = [path]
            self._rafraichir_liste()
            self.after(50, lambda: self._afficher_apercu(path))
            return
        self.lbl_source.configure(text=f"{path}   —   {path.name}")
        self.fichiers = self._scanner(path)
        self._rafraichir_liste()
        self._log(f"Source : {path} — {len(self.fichiers)} fichier(s)")
        if not self.fichiers:
            messagebox.showinfo("MEDICONF", "Aucun fichier image, document ou PDF dans ce dossier.")

    def _quitter(self) -> None:
        if self.var_cible.get().strip():
            _enregistrer_cible(self, self.var_cible.get())
        menu = getattr(self, "_menu_principal", None)
        try:
            self.destroy()
        except Exception:
            pass
        if menu is not None:
            try:
                menu.deiconify()
                menu.lift()
                return
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
    cls._charger_source = _charger_source
    cls._sauver_et_rescan = _sauver_et_rescan
    cls._quitter = _quitter


def brancher(fen, menu) -> None:
    import tkinter as tk
    fen._menu_principal = menu
    tk.Button(fen, text="Retour au menu", command=fen._quitter).place(relx=1.0, rely=0.0, x=-10, y=6, anchor="ne")
    fen.protocol("WM_DELETE_WINDOW", fen._quitter)
    fen.zone_drop.bind("<Button-1>", fen._clic_liste)
    try:
        fen.filtre_images.set(True)
        fen.filtre_docs.set(True)
    except Exception:
        pass

    def relier(w):
        for enfant in w.winfo_children():
            try:
                txt = str(enfant.cget("text")).lower()
            except Exception:
                txt = ""
            try:
                if "sous-dossier" in txt:
                    enfant.configure(command=fen._sauver_et_rescan)
                if txt in ("images", "documents"):
                    enfant.configure(command=fen._rafraichir_liste)
            except Exception:
                pass
            relier(enfant)
    relier(fen)
