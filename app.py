# -*- coding: utf-8 -*-
"""Convertisseur PDF — images et documents bureautique vers PDF."""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from conversion import (
    EXTENSIONS_OK,
    convertir_fichier,
    est_document,
    est_image,
    nom_pdf_cible,
)
from parametres import Parametres

APP_TITRE = "MEDICONF \u2014 Convertisseur PDF"
COULEUR_FOND = "#f4f6f8"
COULEUR_ACCENT = "#1f4e79"
COULEUR_ZONE = "#ffffff"


def ressource_ok(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in EXTENSIONS_OK


class ConvertisseurApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITRE)
        self.geometry("1180x720")
        self.minsize(960, 600)
        self.configure(bg=COULEUR_FOND)
        self.params = Parametres.charger()
        self.source_path: Path | None = None
        self.fichiers: list[Path] = []
        self.vars_coche: dict[str, bool] = {}
        self.apercu_img = None
        self.conversion_en_cours = False
        self.filtre_images = tk.BooleanVar(value=True)
        self.filtre_docs = tk.BooleanVar(value=True)
        self._style()
        self._construire()
        self.protocol("WM_DELETE_WINDOW", self._quitter)

    def _style(self) -> None:
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TFrame", background=COULEUR_FOND)
        s.configure("TLabel", background=COULEUR_FOND, font=("Segoe UI", 10))
        s.configure("Titre.TLabel", background=COULEUR_FOND, font=("Segoe UI", 16, "bold"), foreground=COULEUR_ACCENT)
        s.configure("Info.TLabel", background=COULEUR_FOND, font=("Segoe UI", 9), foreground="#333")
        s.configure("TButton", font=("Segoe UI", 9), padding=6)
        s.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(14, 6))
        s.configure("TCheckbutton", background=COULEUR_FOND, font=("Segoe UI", 10))

    def _construire(self) -> None:
        ttk.Label(self, text=APP_TITRE, style="Titre.TLabel").pack(anchor="w", padx=16, pady=(12, 4))
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.onglet_principal = ttk.Frame(nb)
        self.onglet_params = ttk.Frame(nb)
        nb.add(self.onglet_principal, text="  Conversion  ")
        nb.add(self.onglet_params, text="  Param\u00e8tres  ")
        self._onglet_principal()
        self._onglet_params()

    def _onglet_params(self) -> None:
        p = self.onglet_params
        bloc = ttk.LabelFrame(p, text=" Dossier cible ", padding=12)
        bloc.pack(fill="x", padx=16, pady=16)
        self.var_cible = tk.StringVar(value=self.params.dossier_cible)
        ttk.Label(bloc, text="Chemin du dossier o\u00f9 seront enregistr\u00e9s les PDF :").pack(anchor="w")
        ligne = ttk.Frame(bloc)
        ligne.pack(fill="x", pady=6)
        ttk.Entry(ligne, textvariable=self.var_cible).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(ligne, text="Parcourir\u2026", command=self._parcourir_cible).pack(side="left", padx=(0, 8))
        ttk.Button(ligne, text="Choisir ce dossier", command=self._valider_cible).pack(side="left")
        opts = ttk.LabelFrame(p, text=" Options de parcours et de conversion ", padding=12)
        opts.pack(fill="x", padx=16, pady=8)
        self.var_sous = tk.BooleanVar(value=self.params.parcourir_sous_dossiers)
        ttk.Checkbutton(opts, text="Parcourir les sous-dossiers", variable=self.var_sous, command=self._sauver_params).pack(anchor="w", pady=3)
        self.var_arbo = tk.BooleanVar(value=self.params.conserver_arborescence)
        ttk.Checkbutton(opts, text="Conserver l'arborescence dans le dossier cible", variable=self.var_arbo, command=self._sauver_params).pack(anchor="w", pady=3)
        self.var_comp = tk.BooleanVar(value=self.params.compression)
        ttk.Checkbutton(opts, text="Compresser les images avant le PDF", variable=self.var_comp, command=self._sauver_params).pack(anchor="w", pady=3)
        qligne = ttk.Frame(opts)
        qligne.pack(fill="x", pady=8)
        ttk.Label(qligne, text="Qualit\u00e9 de compression :").pack(side="left")
        self.var_qualite = tk.IntVar(value=self.params.qualite_compression)
        self.lbl_qualite = ttk.Label(qligne, text=f"{self.var_qualite.get()} %")
        self.lbl_qualite.pack(side="right")
        self.scale_qualite = ttk.Scale(opts, from_=40, to=95, orient="horizontal", command=self._chg_qualite)
        self.scale_qualite.set(self.params.qualite_compression)
        self.scale_qualite.pack(fill="x", pady=(0, 8))
        conflit = ttk.LabelFrame(p, text=" Si un PDF du m\u00eame nom existe d\u00e9j\u00e0 ", padding=12)
        conflit.pack(fill="x", padx=16, pady=8)
        self.var_conflit = tk.StringVar(value=self.params.conflit)
        for val, txt in (
            ("renommer", "Renommer automatiquement (fichier_2.pdf, fichier_3.pdf\u2026)"),
            ("ecraser", "\u00c9craser le fichier existant"),
            ("demander", "Demander \u00e0 chaque fois"),
        ):
            ttk.Radiobutton(conflit, text=txt, value=val, variable=self.var_conflit, command=self._sauver_params).pack(anchor="w", pady=2)
        ttk.Label(p, text="Les param\u00e8tres sont enregistr\u00e9s automatiquement.", style="Info.TLabel").pack(anchor="w", padx=16, pady=8)

    def _chg_qualite(self, _evt=None) -> None:
        v = int(float(self.scale_qualite.get()))
        self.var_qualite.set(v)
        self.lbl_qualite.configure(text=f"{v} %")
        self._sauver_params()

    def _parcourir_cible(self) -> None:
        initial = self.var_cible.get().strip() or str(Path.home())
        d = filedialog.askdirectory(title="Choisir le dossier cible", initialdir=initial)
        if d:
            self.var_cible.set(d)

    def _valider_cible(self) -> None:
        d = self.var_cible.get().strip()
        if not d:
            messagebox.showwarning(APP_TITRE, "Indiquez un dossier cible.")
            return
        p = Path(d)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror(APP_TITRE, f"Impossible d'utiliser ce dossier :\n{e}")
            return
        if not p.is_dir():
            messagebox.showerror(APP_TITRE, "Ce chemin n'est pas un dossier valide.")
            return
        self.params.dossier_cible = str(p)
        self._sauver_params()
        messagebox.showinfo(APP_TITRE, f"Dossier cible enregistr\u00e9 :\n{p}")

    def _sauver_params(self) -> None:
        self.params.dossier_cible = self.var_cible.get().strip()
        self.params.parcourir_sous_dossiers = self.var_sous.get()
        self.params.compression = self.var_comp.get()
        self.params.qualite_compression = int(self.var_qualite.get())
        self.params.conserver_arborescence = self.var_arbo.get()
        self.params.conflit = self.var_conflit.get()
        try:
            self.params.sauvegarder()
        except Exception:
            pass

    def _onglet_principal(self) -> None:
        p = self.onglet_principal
        haut = ttk.Frame(p)
        haut.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(haut, text="Source :").pack(side="left")
        self.lbl_source = ttk.Label(haut, text="(aucun fichier ni dossier)", style="Info.TLabel")
        self.lbl_source.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(haut, text="Parcourir\u2026", command=self._parcourir_source).pack(side="left", padx=4)
        ttk.Button(haut, text="S\u00e9lectionner ce dossier source", command=self._choisir_dossier_source).pack(side="left")
        filtres = ttk.Frame(p)
        filtres.pack(fill="x", padx=12, pady=4)
        ttk.Label(filtres, text="Afficher :").pack(side="left")
        ttk.Checkbutton(filtres, text="Images", variable=self.filtre_images, command=self._rafraichir_liste).pack(side="left", padx=8)
        ttk.Checkbutton(filtres, text="Documents", variable=self.filtre_docs, command=self._rafraichir_liste).pack(side="left", padx=8)
        ttk.Button(filtres, text="Tout cocher", command=self._tout_cocher).pack(side="left", padx=(16, 4))
        ttk.Button(filtres, text="Tout d\u00e9cocher", command=self._tout_decocher).pack(side="left")
        corps = ttk.Frame(p)
        corps.pack(fill="both", expand=True, padx=12, pady=6)
        corps.columnconfigure(0, weight=3)
        corps.columnconfigure(1, weight=2)
        corps.rowconfigure(0, weight=1)
        gauche = ttk.LabelFrame(corps, text=" Fichiers source ", padding=6)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        gauche.rowconfigure(0, weight=1)
        gauche.columnconfigure(0, weight=1)
        self.zone_drop = tk.Listbox(gauche, selectmode="browse", font=("Segoe UI", 10), activestyle="dotbox", bg=COULEUR_ZONE)
        sb = ttk.Scrollbar(gauche, orient="vertical", command=self.zone_drop.yview)
        self.zone_drop.configure(yscrollcommand=sb.set)
        self.zone_drop.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.zone_drop.bind("<Button-1>", self._clic_liste)
        droite = ttk.LabelFrame(corps, text=" Aper\u00e7u ", padding=6)
        droite.grid(row=0, column=1, sticky="nsew")
        self.canvas_apercu = tk.Canvas(droite, bg="#e8eaed", highlightthickness=0)
        self.canvas_apercu.pack(fill="both", expand=True)
        self.lbl_apercu_info = ttk.Label(droite, text="")
        self.lbl_apercu_info.pack(fill="x", pady=(6, 0))
        actions = ttk.Frame(p)
        actions.pack(fill="x", padx=12, pady=4)
        self.btn_convertir = ttk.Button(actions, text="Tout convertir", command=self._tout_convertir)
        self.btn_convertir.pack(side="left")
        ttk.Button(actions, text="Effacer la s\u00e9lection", command=self._effacer).pack(side="left", padx=8)
        ttk.Button(actions, text="Ouvrir le dossier cible", command=self._ouvrir_cible).pack(side="left")
        self.progress = ttk.Progressbar(p, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(4, 2))
        journal_fr = ttk.LabelFrame(p, text=" Journal de conversion ", padding=4)
        journal_fr.pack(fill="x", padx=12, pady=(0, 8))
        self.journal = tk.Text(journal_fr, height=6, font=("Consolas", 9), wrap="word", bg="#fff")
        jsb = ttk.Scrollbar(journal_fr, command=self.journal.yview)
        self.journal.configure(yscrollcommand=jsb.set)
        self.journal.pack(side="left", fill="both", expand=True)
        jsb.pack(side="right", fill="y")
        self.journal.configure(state="disabled")
        self._log("Parcourir un fichier ou s\u00e9lectionner un dossier source pour commencer.")

    def _parcourir_source(self) -> None:
        if messagebox.askquestion(APP_TITRE, "Oui = dossier\nNon = fichier unique", icon="question") == "yes":
            self._choisir_dossier_source()
            return
        types = [("Fichiers convertibles", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp *.ico *.jfif *.txt *.rtf *.doc *.docx *.odt"), ("Tous", "*.*")]
        f = filedialog.askopenfilename(title="Choisir un fichier source", filetypes=types)
        if f:
            self._charger_source(Path(f))

    def _choisir_dossier_source(self) -> None:
        d = filedialog.askdirectory(title="S\u00e9lectionner ce dossier source")
        if d:
            self._charger_source(Path(d))

    def _charger_source(self, path: Path) -> None:
        path = Path(path)
        if not path.exists():
            messagebox.showerror(APP_TITRE, "Chemin introuvable.")
            return
        self.source_path = path
        if path.is_file():
            self.lbl_source.configure(text=f"{path.parent}   \u2014   {path.name}")
            if not ressource_ok(path):
                messagebox.showwarning(APP_TITRE, "Type de fichier non pris en charge.")
                return
            self.fichiers = [path]
            self._rafraichir_liste()
            if messagebox.askyesno(APP_TITRE, f"Convertir ce fichier en PDF maintenant ?\n\n{path.name}"):
                self._convertir_un_fichier(path)
            return
        self.lbl_source.configure(text=f"{path}   \u2014   {path.name}")
        self.fichiers = self._scanner(path)
        if not self.fichiers:
            messagebox.showinfo(APP_TITRE, "Aucun fichier image ou bureautique trouv\u00e9.")
        self._rafraichir_liste()

    def _scanner(self, racine: Path) -> list[Path]:
        fichiers: list[Path] = []
        if self.var_sous.get():
            for dirpath, _dns, names in os.walk(racine):
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

    def _visible(self) -> list[Path]:
        out = []
        for p in self.fichiers:
            if est_image(p) and not self.filtre_images.get():
                continue
            if est_document(p) and not self.filtre_docs.get():
                continue
            out.append(p)
        return out

    def _libelle(self, p: Path) -> str:
        if self.source_path and self.source_path.is_dir() and self.var_sous.get():
            try:
                return str(p.relative_to(self.source_path))
            except ValueError:
                return p.name
        return p.name

    def _rafraichir_liste(self) -> None:
        self.zone_drop.delete(0, "end")
        for p in self._visible():
            key = str(p)
            if key not in self.vars_coche:
                self.vars_coche[key] = True
            marque = "\u2611" if self.vars_coche.get(key, True) else "\u2610"
            self.zone_drop.insert("end", f" {marque}  {self._libelle(p)}")

    def _clic_liste(self, event) -> str:
        idx = self.zone_drop.nearest(event.y)
        visibles = self._visible()
        if idx < 0 or idx >= len(visibles):
            return "break"
        p = visibles[idx]
        if event.x < 28:
            self.vars_coche[str(p)] = not self.vars_coche.get(str(p), True)
            self._rafraichir_liste()
            self.zone_drop.selection_set(idx)
        else:
            self.zone_drop.selection_clear(0, "end")
            self.zone_drop.selection_set(idx)
            self._afficher_apercu(p)
        return "break"

    def _afficher_apercu(self, path: Path) -> None:
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text=f"{path.name}  \u2014  {self._taille(path)}")
        self.canvas_apercu.update_idletasks()
        cw = max(self.canvas_apercu.winfo_width(), 120)
        ch = max(self.canvas_apercu.winfo_height(), 120)
        if est_image(path):
            try:
                im = Image.open(path)
                im.thumbnail((cw - 16, ch - 16), Image.Resampling.LANCZOS)
                self.apercu_img = ImageTk.PhotoImage(im)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
            except Exception as e:
                self.canvas_apercu.create_text(cw // 2, ch // 2, text=f"Aper\u00e7u impossible\n{e}", fill="#444", font=("Segoe UI", 10))
            return
        extra = path.name
        try:
            if path.suffix.lower() == ".txt":
                extra = path.read_text(encoding="utf-8", errors="replace")[:800]
            elif path.suffix.lower() == ".docx":
                import zipfile
                import xml.etree.ElementTree as ET
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                with zipfile.ZipFile(path) as z:
                    root = ET.fromstring(z.read("word/document.xml"))
                lignes = ["".join(t.text or "" for t in para.iter(ns + "t")) for para in root.iter(ns + "p")]
                extra = "\n".join(lignes)[:700]
            else:
                extra = f"Document {path.suffix.upper()}\n\nAper\u00e7u visuel indisponible.\nLibreOffice sera utilis\u00e9 s'il est install\u00e9."
        except Exception as e:
            extra = str(e)
        self.canvas_apercu.create_text(12, 12, anchor="nw", text=extra, width=cw - 24, fill="#222", font=("Segoe UI", 9))

    def _taille(self, p: Path) -> str:
        try:
            n = float(p.stat().st_size)
        except OSError:
            return "?"
        for u in ("o", "Ko", "Mo", "Go"):
            if n < 1024 or u == "Go":
                return f"{n:.0f} {u}" if u == "o" else f"{n:.1f} {u}"
            n /= 1024
        return ""

    def _tout_cocher(self) -> None:
        for p in self._visible():
            self.vars_coche[str(p)] = True
        self._rafraichir_liste()

    def _tout_decocher(self) -> None:
        for p in self._visible():
            self.vars_coche[str(p)] = False
        self._rafraichir_liste()

    def _selectionnes(self) -> list[Path]:
        return [p for p in self._visible() if self.vars_coche.get(str(p), True)]

    def _cible_ok(self) -> Path | None:
        d = self.var_cible.get().strip() or self.params.dossier_cible
        if not d:
            messagebox.showwarning(APP_TITRE, "D\u00e9finissez un dossier cible dans Param\u00e8tres, puis \u00ab Choisir ce dossier \u00bb.")
            return None
        p = Path(d)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror(APP_TITRE, f"Dossier cible invalide :\n{e}")
            return None
        return p

    def _resoudre_conflit(self, dest: Path, source: Path) -> Path | None:
        if not dest.exists() or self.var_conflit.get() != "demander":
            return dest
        r = messagebox.askyesnocancel(APP_TITRE, f"Le fichier existe d\u00e9j\u00e0 :\n{dest.name}\n\nOui = \u00e9craser\nNon = renommer\nAnnuler = ignorer")
        if r is None:
            return None
        if r:
            return dest
        return nom_pdf_cible(source, dest.parent, None, False, "renommer")

    def _convertir_un_fichier(self, source: Path) -> None:
        cible = self._cible_ok()
        if cible is None:
            return
        dest = nom_pdf_cible(source, cible, self.source_path if self.source_path and self.source_path.is_dir() else None, self.var_arbo.get(), self.var_conflit.get() if self.var_conflit.get() != "demander" else "renommer")
        dest2 = self._resoudre_conflit(dest, source)
        if dest2 is None:
            self._log(f"Ignor\u00e9 : {source.name}")
            return
        try:
            warn = convertir_fichier(source, dest2, self.var_comp.get(), int(self.var_qualite.get()))
            self._log(f"OK  {source.name}  \u2192  {dest2}")
            if warn:
                self._log(f"    note : {warn}")
            messagebox.showinfo(APP_TITRE, f"PDF enregistr\u00e9 :\n{dest2}")
        except Exception as e:
            self._log(f"ERREUR  {source.name} : {e}")
            messagebox.showerror(APP_TITRE, f"Conversion impossible :\n{e}")

    def _tout_convertir(self) -> None:
        if self.conversion_en_cours:
            return
        fichiers = self._selectionnes()
        if not fichiers:
            messagebox.showinfo(APP_TITRE, "Aucun fichier coch\u00e9.")
            return
        cible = self._cible_ok()
        if cible is None:
            return
        if not messagebox.askyesno(APP_TITRE, f"Convertir {len(fichiers)} fichier(s) vers :\n{cible} ?"):
            return
        self.conversion_en_cours = True
        self.btn_convertir.configure(state="disabled")
        self.progress.configure(maximum=len(fichiers), value=0)
        racine = self.source_path if self.source_path and self.source_path.is_dir() else None

        def travail():
            ok = ko = 0
            for i, source in enumerate(fichiers, 1):
                dest = nom_pdf_cible(source, cible, racine, self.var_arbo.get(), "renommer" if self.var_conflit.get() == "demander" else self.var_conflit.get())
                try:
                    warn = convertir_fichier(source, dest, self.var_comp.get(), int(self.var_qualite.get()))
                    ok += 1
                    msg = f"OK  {self._libelle(source)}  \u2192  {dest.name}"
                    if warn:
                        msg += f"  ({warn})"
                    self.after(0, lambda m=msg: self._log(m))
                except Exception as e:
                    ko += 1
                    self.after(0, lambda s=source, err=str(e): self._log(f"ERREUR  {s.name} : {err}"))
                self.after(0, lambda v=i: self.progress.configure(value=v))

            def fin():
                self.conversion_en_cours = False
                self.btn_convertir.configure(state="normal")
                self._log(f"Termin\u00e9 : {ok} r\u00e9ussi(s), {ko} \u00e9chec(s).")
                messagebox.showinfo(APP_TITRE, f"Conversion termin\u00e9e.\nR\u00e9ussis : {ok}\n\u00c9checs : {ko}")

            self.after(0, fin)

        threading.Thread(target=travail, daemon=True).start()

    def _effacer(self) -> None:
        self.source_path = None
        self.fichiers = []
        self.vars_coche = {}
        self.lbl_source.configure(text="(aucun fichier ni dossier)")
        self.zone_drop.delete(0, "end")
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text="")
        self.progress.configure(value=0)
        self._log("S\u00e9lection effac\u00e9e.")

    def _ouvrir_cible(self) -> None:
        d = self.var_cible.get().strip() or self.params.dossier_cible
        if not d or not Path(d).is_dir():
            messagebox.showwarning(APP_TITRE, "Aucun dossier cible valide.")
            return
        if sys.platform.startswith("win"):
            os.startfile(d)  # type: ignore
        elif sys.platform == "darwin":
            os.system(f'open "{d}"')
        else:
            os.system(f'xdg-open "{d}"')

    def _log(self, msg: str) -> None:
        self.journal.configure(state="normal")
        self.journal.insert("end", msg + "\n")
        self.journal.see("end")
        self.journal.configure(state="disabled")

    def _quitter(self) -> None:
        self._sauver_params()
        self.destroy()


def main() -> None:
    ConvertisseurApp().mainloop()


if __name__ == "__main__":
    main()
