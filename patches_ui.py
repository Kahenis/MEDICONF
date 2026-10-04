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


def dialogue_explorateur(parent, titre: str, dossiers: bool = True, afficher_fichiers: bool = False) -> str:
    """Dialogue natif de l'Explorateur Windows (IFileDialog) : reseau, lecteurs, chemin reel."""
    if afficher_fichiers and dossiers and os.name == "nt":
        return _dialogue_selection_dossier(parent, titre)
    if os.name != "nt":
        if dossiers:
            return filedialog.askdirectory(title=titre, parent=parent) or ""
        return filedialog.askopenfilename(title=titre, parent=parent) or ""
    try:
        return _dialogue_com(parent, titre, dossiers)
    except Exception as e:
        messagebox.showerror("MEDICONF", f"Dialogue Windows indisponible :\n{e}", parent=parent)
        if dossiers:
            return filedialog.askdirectory(title=titre, parent=parent) or ""
        return filedialog.askopenfilename(title=titre, parent=parent) or ""


def _dialogue_selection_dossier(parent, titre: str) -> str:
    """Fichiers visibles. Double-clic = entrer. Sélectionner = retenir le dossier affiché."""
    import uuid
    from ctypes import POINTER, WINFUNCTYPE, byref, c_void_p, cast, sizeof, windll, HRESULT, c_uint
    from ctypes.wintypes import DWORD, HWND, LPWSTR, BOOL

    choix = {"chemin": ""}
    ole32 = windll.ole32
    ole32.CoInitialize.argtypes = [c_void_p]
    ole32.CoInitialize.restype = HRESULT
    ole32.CoCreateInstance.argtypes = [c_void_p, c_void_p, DWORD, c_void_p, POINTER(c_void_p)]
    ole32.CoCreateInstance.restype = HRESULT
    ole32.CoTaskMemFree.argtypes = [c_void_p]
    hr = ole32.CoInitialize(None)
    if hr < 0 and (hr & 0xFFFFFFFF) != 0x80010106:
        return _dialogue_com(parent, titre, True)

    def methode(obj, index, proto):
        vtbl = cast(obj, POINTER(c_void_p))[0]
        return cast(vtbl + index * sizeof(c_void_p), POINTER(proto))[0]

    clsid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}").bytes_le)
    iid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("{D57C7288-D4AD-4768-BE02-9D969532D960}").bytes_le)
    com = c_void_p()
    if ole32.CoCreateInstance(clsid, None, 1, iid, byref(com)) < 0 or not com.value:
        return _dialogue_com(parent, titre, True)

    release = methode(com, 2, WINFUNCTYPE(HRESULT, c_void_p))
    show = methode(com, 3, WINFUNCTYPE(HRESULT, c_void_p, HWND))
    set_types = methode(com, 4, WINFUNCTYPE(HRESULT, c_void_p, c_uint, c_void_p))
    advise = methode(com, 7, WINFUNCTYPE(HRESULT, c_void_p, c_void_p, POINTER(DWORD)))
    set_options = methode(com, 9, WINFUNCTYPE(HRESULT, c_void_p, DWORD))
    get_options = methode(com, 10, WINFUNCTYPE(HRESULT, c_void_p, POINTER(DWORD)))
    get_folder = methode(com, 13, WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_void_p)))
    set_title = methode(com, 17, WINFUNCTYPE(HRESULT, c_void_p, LPWSTR))
    set_ok = methode(com, 18, WINFUNCTYPE(HRESULT, c_void_p, LPWSTR))
    close_dlg = methode(com, 23, WINFUNCTYPE(HRESULT, c_void_p, HRESULT))
    qi = methode(com, 0, WINFUNCTYPE(HRESULT, c_void_p, c_void_p, POINTER(c_void_p)))
    try:
        flags = DWORD()
        get_options(com, byref(flags))
        flags.value |= 0x40 | 0x800 | 0x1000
        flags.value &= ~0x20
        set_options(com, flags)
        class _Filtre(ctypes.Structure):
            _fields_ = [("pszName", ctypes.c_wchar_p), ("pszSpec", ctypes.c_wchar_p)]
        spec = _Filtre("Tous les fichiers (*.*)", "*.*")
        set_types(com, 1, ctypes.byref(spec))
        set_title(com, titre + " — double-clic pour entrer, Sélectionner pour choisir ce dossier")
        set_ok(com, "Ouvrir")

        iid_custom = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("{e6fdd21a-163f-4975-9c8c-a69f1ba37034}").bytes_le)
        custom = c_void_p()
        if qi(com, iid_custom, byref(custom)) >= 0 and custom.value:
            add_button = methode(custom, 5, WINFUNCTYPE(HRESULT, c_void_p, DWORD, LPWSTR))
            prominent = methode(custom, 28, WINFUNCTYPE(HRESULT, c_void_p, DWORD))
            add_button(custom, DWORD(101), "Sélectionner")
            prominent(custom, DWORD(101))
            methode(custom, 2, WINFUNCTYPE(HRESULT, c_void_p))(custom)

        def nom_item(item) -> str:
            if not item:
                return ""
            get_name = methode(item, 5, WINFUNCTYPE(HRESULT, c_void_p, DWORD, POINTER(LPWSTR)))
            rel = methode(item, 2, WINFUNCTYPE(HRESULT, c_void_p))
            nom = LPWSTR()
            try:
                if get_name(item, DWORD(0x80058000), byref(nom)) < 0 or not nom.value:
                    return ""
                return nom.value
            finally:
                if nom:
                    ole32.CoTaskMemFree(cast(nom, c_void_p))
                rel(item)

        def retenir_dossier():
            item = c_void_p()
            if get_folder(com, byref(item)) < 0:
                return
            chemin = nom_item(item.value)
            if chemin:
                p = Path(chemin)
                choix["chemin"] = str(p.parent if p.is_file() else p)
                close_dlg(com, HRESULT(0))

        @ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, POINTER(c_void_p))
        def events_qi(_this, riid, out):
            out[0] = ctypes.addressof(events)
            return 0

        @ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
        def events_add(_this):
            return 1

        @ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD)
        def on_button(_this, _custom, ctl):
            if ctl == 101:
                retenir_dossier()
            return 0

        @ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)
        def on_file_ok(_this, _dlg):
            retenir_dossier()
            return 0

        fn_qi = events_qi
        fn_add = events_add
        fn_rel = events_add
        fn_ok = on_file_ok
        fn_ignore = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)(lambda *_a: 0)
        fn_ignore2 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, c_void_p)(lambda *_a: 0)
        fn_button = on_button
        fn_ctl = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD, DWORD)(lambda *_a: 0)
        fn_check = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD, BOOL)(lambda *_a: 0)
        vtbl_events = (c_void_p * 10)(
            cast(fn_qi, c_void_p), cast(fn_add, c_void_p), cast(fn_rel, c_void_p),
            cast(fn_ok, c_void_p), cast(fn_ignore2, c_void_p), cast(fn_ignore, c_void_p),
            cast(fn_ignore, c_void_p), cast(fn_ignore2, c_void_p), cast(fn_ignore, c_void_p),
            cast(fn_ignore2, c_void_p),
        )
        vtbl_ctrl = (c_void_p * 7)(
            cast(fn_qi, c_void_p), cast(fn_add, c_void_p), cast(fn_rel, c_void_p),
            cast(fn_ctl, c_void_p), cast(fn_button, c_void_p), cast(fn_check, c_void_p),
            cast(fn_ctl, c_void_p),
        )
        events = c_void_p(ctypes.addressof(vtbl_events))
        events = ctypes.pointer(c_void_p(ctypes.addressof(vtbl_events)))
        ctrl = ctypes.pointer(c_void_p(ctypes.addressof(vtbl_ctrl)))
        def events_qi_reel(_this, riid, out):
            try:
                voulu = uuid.UUID(bytes_le=bytes(cast(riid, POINTER(ctypes.c_byte * 16)).contents))
            except Exception:
                out[0] = 0
                return HRESULT(0x80004002)
            if voulu in (uuid.UUID("{973510db-7d7f-452b-8975-74a85828d354}"), uuid.UUID("{00000000-0000-0000-C000-000000000046}")):
                out[0] = ctypes.addressof(events.contents)
            elif voulu == uuid.UUID("{36116642-D713-4b97-9B83-7484A9D00433}"):
                out[0] = ctypes.addressof(ctrl.contents)
            else:
                out[0] = 0
                return HRESULT(0x80004002)
            return 0
        fn_qi = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(events_qi_reel)
        vtbl_events[0] = cast(fn_qi, c_void_p)
        vtbl_ctrl[0] = cast(fn_qi, c_void_p)
        cookie = DWORD()
        advise(com, events, byref(cookie))
        hwnd = 0
        try:
            hwnd = int(parent.winfo_id())
        except Exception:
            hwnd = 0
        show(com, HWND(hwnd))
        try:
            windll.user32.EnableWindow(HWND(hwnd), 1)
        except Exception:
            pass
        return choix["chemin"]
    finally:
        release(com)


def _dialogue_com(parent, titre: str, dossiers: bool, forcer_tous_fichiers: bool = False) -> str:
    import uuid
    from ctypes import POINTER, WINFUNCTYPE, byref, c_void_p, cast, sizeof, windll, HRESULT
    from ctypes.wintypes import DWORD, HWND, LPWSTR

    ole32 = windll.ole32
    ole32.CoInitialize.argtypes = [c_void_p]
    ole32.CoInitialize.restype = HRESULT
    ole32.CoCreateInstance.argtypes = [c_void_p, c_void_p, DWORD, c_void_p, POINTER(c_void_p)]
    ole32.CoCreateInstance.restype = HRESULT
    ole32.CoTaskMemFree.argtypes = [c_void_p]
    ole32.CoTaskMemFree.restype = None

    hr = ole32.CoInitialize(None)
    if hr < 0 and (hr & 0xFFFFFFFF) != 0x80010106:
        raise OSError(f"CoInitialize {hr & 0xFFFFFFFF:08X}")

    clsid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}").bytes_le)
    iid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("{D57C7288-D4AD-4768-BE02-9D969532D960}").bytes_le)
    com = c_void_p()
    hr = ole32.CoCreateInstance(clsid, None, 1, iid, byref(com))
    if hr < 0 or not com.value:
        raise OSError(f"IFileOpenDialog {hr & 0xFFFFFFFF:08X}")

    def methode(obj, index, proto):
        vtbl = cast(obj, POINTER(c_void_p))[0]
        return cast(vtbl + index * sizeof(c_void_p), POINTER(proto))[0]

    release = methode(com, 2, WINFUNCTYPE(HRESULT, c_void_p))
    show = methode(com, 3, WINFUNCTYPE(HRESULT, c_void_p, HWND))
    set_types = methode(com, 4, WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint, ctypes.c_void_p))
    set_options = methode(com, 9, WINFUNCTYPE(HRESULT, c_void_p, DWORD))
    get_options = methode(com, 10, WINFUNCTYPE(HRESULT, c_void_p, POINTER(DWORD)))
    set_title = methode(com, 17, WINFUNCTYPE(HRESULT, c_void_p, LPWSTR))
    set_ok = methode(com, 18, WINFUNCTYPE(HRESULT, c_void_p, LPWSTR))
    get_result = methode(com, 20, WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_void_p)))
    try:
        flags = DWORD()
        get_options(com, byref(flags))
        flags.value |= 0x40 | 0x800
        if dossiers and not forcer_tous_fichiers:
            flags.value |= 0x20
        else:
            flags.value |= 0x1000
        set_options(com, flags)
        if forcer_tous_fichiers:
            class _Filtre(ctypes.Structure):
                _fields_ = [("pszName", ctypes.c_wchar_p), ("pszSpec", ctypes.c_wchar_p)]
            spec = _Filtre("Tous les fichiers (*.*)", "*.*")
            set_types(com, 1, ctypes.byref(spec))
        set_title(com, titre)
        set_ok(com, "Choisir ce dossier" if dossiers else "Selectionner")
        hwnd = 0
        try:
            hwnd = int(parent.winfo_id())
        except Exception:
            hwnd = 0
        hr = show(com, HWND(hwnd))
        try:
            windll.user32.EnableWindow(HWND(hwnd), 1)
        except Exception:
            pass
        if hr < 0:
            return ""
        item = c_void_p()
        if get_result(com, byref(item)) < 0 or not item.value:
            get_folder = methode(com, 13, WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_void_p)))
            if get_folder(com, byref(item)) < 0 or not item.value:
                return ""
        get_name = methode(item, 5, WINFUNCTYPE(HRESULT, c_void_p, DWORD, POINTER(LPWSTR)))
        rel_item = methode(item, 2, WINFUNCTYPE(HRESULT, c_void_p))
        nom = LPWSTR()
        try:
            if get_name(item, DWORD(0x80058000), byref(nom)) < 0 or not nom.value:
                return ""
            return nom.value
        finally:
            if nom:
                ole32.CoTaskMemFree(cast(nom, c_void_p))
            rel_item(item)
    finally:
        release(com)


def _enregistrer_cible(fen, chemin: str) -> bool:
    chemin = (chemin or "").strip().strip('"')
    if not chemin:
        return False
    fen.var_cible.set(chemin)
    try:
        fen.update_idletasks()
    except Exception:
        pass
    fen.params.dossier_cible = chemin
    try:
        fen.params.sauvegarder()
    except Exception:
        pass
    try:
        fen._log(f"Dossier cible : {chemin}")
    except Exception:
        pass
    return True


def _cases(fen):
    trouves = []

    def walk(w):
        for enfant in w.winfo_children():
            try:
                txt = str(enfant.cget("text")).lower()
            except Exception:
                txt = ""
            if txt:
                trouves.append((txt, enfant))
            walk(enfant)

    walk(fen)
    return trouves


def _coche(widget) -> bool:
    try:
        return bool(widget.instate(["selected"]))
    except Exception:
        return False


def appliquer(cls) -> None:
    def _parcourir_cible(self) -> None:
        d = dialogue_explorateur(self, "Choisir le dossier cible", True)
        if not d:
            messagebox.showwarning("MEDICONF", "Aucun dossier n'a été renvoyé.", parent=self)
            return
        self._dernier_cible = d
        _enregistrer_cible(self, d)

    def _valider_cible(self) -> None:
        d = self.var_cible.get().strip() or getattr(self, "_dernier_cible", "")
        if not d:
            messagebox.showwarning("MEDICONF", "Choisissez d'abord un dossier avec Parcourir.", parent=self)
            return
        if _enregistrer_cible(self, d):
            messagebox.showinfo("MEDICONF", f"Dossier cible enregistré :\n{d}", parent=self)

    def _parcourir_source(self) -> None:
        type_sel = choisir_type_source(self)
        if type_sel == "dossier":
            self._choisir_dossier_source()
        elif type_sel == "fichier":
            f = dialogue_explorateur(self, "Choisir un fichier source", False)
            if f:
                self._charger_source(Path(f))

    def _choisir_dossier_source(self) -> None:
        d = dialogue_explorateur(self, "Sélectionner le dossier source", True, afficher_fichiers=True)
        if d:
            self._charger_source(Path(d))

    def _sous_actif(self) -> bool:
        for txt, w in _cases(self):
            if "sous-dossier" in txt:
                return _coche(w)
        return bool(self.var_sous.get())

    def _scanner(self, racine: Path):
        fichiers = []
        racine = Path(racine)
        profond = bool(self.var_sous.get()) or self._sous_actif()
        try:
            if profond:
                for dirpath, _dirs, names in os.walk(racine):
                    for n in names:
                        p = Path(dirpath) / n
                        if p.is_file():
                            fichiers.append(p)
            else:
                for p in racine.iterdir():
                    if p.is_file():
                        fichiers.append(p)
        except Exception as e:
            self._log(f"Lecture impossible : {e}")
        fichiers.sort(key=lambda x: str(x).lower())
        return fichiers

    def _sauver_et_rescan(self) -> None:
        self.after(80, self._rescan_sous)

    def _rescan_sous(self) -> None:
        actif = self._sous_actif()
        try:
            self.var_sous.set(actif)
            self.params.parcourir_sous_dossiers = actif
            self.params.sauvegarder()
        except Exception:
            pass
        if getattr(self, "source_path", None) and Path(self.source_path).is_dir():
            self.fichiers = self._scanner(self.source_path)
            self._rafraichir_liste()
            self._log(f"{len(self.fichiers)} fichier(s) — sous-dossiers : {'oui' if actif else 'non'}")

    def _filtres_actifs(self):
        voir_img, voir_doc = True, True
        for txt, w in _cases(self):
            if txt == "images":
                voir_img = _coche(w)
            elif txt == "documents":
                voir_doc = _coche(w)
        return voir_img, voir_doc

    def _visible(self):
        return list(self.fichiers)

    def _rafraichir_liste(self) -> None:
        self.zone_drop.delete(0, "end")
        self._index_visible = list(self.fichiers)
        for p in self._index_visible:
            key = str(p)
            if key not in self.vars_coche:
                self.vars_coche[key] = True
            marque = "\u2611" if self.vars_coche.get(key, True) else "\u2610"
            self.zone_drop.insert("end", f" {marque}  {self._libelle(p)}")
        self._log(f"Liste : {len(self._index_visible)} fichier(s)")

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
        self.zone_drop.delete(0, "end")
        self._index_visible = list(self.fichiers)
        for p in self.fichiers:
            self.vars_coche[str(p)] = True
            self.zone_drop.insert("end", f" \u2611  {self._libelle(p)}")
        self._log(f"Source : {path} — {len(self.fichiers)} fichier(s), sous-dossiers : {'oui' if self.var_sous.get() else 'non'}")

    def _quitter(self) -> None:
        try:
            self._sauver_params()
        except Exception:
            pass
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

    cls._parcourir_source = _parcourir_source
    cls._choisir_dossier_source = _choisir_dossier_source
    cls._quitter = _quitter


def brancher(fen, menu) -> None:
    import tkinter as tk
    fen._menu_principal = menu
    tk.Button(fen, text="Retour au menu", command=fen._quitter).place(relx=1.0, rely=0.0, x=-10, y=6, anchor="ne")
    fen.protocol("WM_DELETE_WINDOW", fen._quitter)
    try:
        fen.filtre_images.set(True)
        fen.filtre_docs.set(True)
    except Exception:
        pass

    a_retirer = []

    def relier(w):
        try:
            enfants = list(w.winfo_children())
        except Exception:
            return
        for enfant in enfants:
            try:
                txt = str(enfant.cget("text")).lower()
            except Exception:
                txt = ""
            try:
                if "sous-dossier" in txt:
                    enfant.configure(command=fen._basculer_sous_dossiers)
                if txt in ("images", "documents", "afficher :"):
                    a_retirer.append(enfant)
            except Exception:
                pass
            relier(enfant)

    try:
        relier(fen)
        for enfant in a_retirer:
            try:
                enfant.destroy()
            except Exception:
                pass
    except Exception:
        pass
