# -*- coding: utf-8 -*-
"""Partie 2 : interface de conversion intelligente des PDF scannés vers texte."""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import ImageTk

import apercu_pdf
import themes
from parametres import Parametres

APP_TITRE = "MEDICONF - Conversion intelligente vers texte - Par JF Guilard"
COULEUR_FOND = "#f4f6f8"
COULEUR_ZONE = "#ffffff"


def a_du_vrai_texte(path: Path) -> bool:
    """Vrai si le PDF a déjà une couche de texte sélectionnable."""
    from pypdf import PdfReader
    lecteur = PdfReader(str(path))
    total = 0
    for page in lecteur.pages[:8]:
        brut = page.extract_text() or ""
        total += len("".join(brut.split()))
        if total >= 25:
            return True
    return False


def lister_scans(racine: Path, sous_dossiers: bool) -> tuple[list[Path], int]:
    racine = Path(racine)
    candidats: list[Path] = []
    if sous_dossiers:
        for dossier, _dirs, noms in os.walk(racine):
            for nom in noms:
                p = Path(dossier) / nom
                if p.suffix.lower() == ".pdf":
                    candidats.append(p)
    else:
        try:
            enfants = list(racine.iterdir())
        except OSError:
            enfants = []
        candidats = [p for p in enfants if p.is_file() and p.suffix.lower() == ".pdf"]
    gardes: list[Path] = []
    ecartes = 0
    for p in sorted(candidats, key=lambda x: str(x).lower()):
        try:
            if a_du_vrai_texte(p):
                ecartes += 1
                continue
        except Exception:
            ecartes += 1
            continue
        gardes.append(p)
    return gardes, ecartes


class Partie2App(tk.Toplevel):
    def __init__(self, master=None) -> None:
        super().__init__(master)
        self.title(APP_TITRE)
        self.geometry("1180x720")
        self.minsize(960, 600)
        self.configure(bg=COULEUR_FOND)
        self.params = Parametres.charger()
        self.source_path: Path | None = None
        self.fichiers: list[Path] = []
        self.vars_coche: dict[str, bool] = {}
        self.apercu_img = None
        self._style()
        self._construire()
        self.protocol("WM_DELETE_WINDOW", self._quitter)

    def _style(self) -> None:
        themes.appliquer(self)

    def _construire(self) -> None:
        ttk.Label(self, text=APP_TITRE, style="Titre.TLabel").pack(anchor="w", padx=16, pady=(12, 4))
        ttk.Button(self, text="Retour au menu", command=self._quitter).pack(anchor="e", padx=16)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.onglet = ttk.Frame(nb)
        self.onglet_params = ttk.Frame(nb)
        nb.add(self.onglet, text="  Conversion intelligente  ")
        nb.add(self.onglet_params, text="  Paramètres  ")
        self._page()
        self._params()

    def _page(self) -> None:
        p = self.onglet
        haut = ttk.Frame(p)
        haut.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(haut, text="Source :").pack(side="left")
        self.lbl_source = ttk.Label(haut, text="(aucun dossier)", style="Info.TLabel")
        self.lbl_source.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(haut, text="Parcourir…", command=self._parcourir).pack(side="left", padx=4)
        cases = ttk.Frame(p)
        cases.pack(anchor="w", padx=12, pady=(4, 0))
        ttk.Button(cases, text="Tout cocher", command=self._tout_cocher).pack(side="left")
        ttk.Button(cases, text="Tout décocher", command=self._tout_decocher).pack(side="left", padx=8)
        corps = ttk.Frame(p)
        corps.pack(fill="both", expand=True, padx=12, pady=6)
        corps.columnconfigure(0, weight=3)
        corps.columnconfigure(1, weight=2)
        corps.rowconfigure(0, weight=1)
        gauche = ttk.LabelFrame(corps, text=" PDF scannés et PDF image ", padding=6)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        gauche.rowconfigure(0, weight=1)
        gauche.columnconfigure(0, weight=1)
        self.zone = tk.Canvas(gauche, bg=COULEUR_ZONE, highlightthickness=0)
        sb = ttk.Scrollbar(gauche, orient="vertical", command=self.zone.yview)
        self.zone.configure(yscrollcommand=sb.set)
        self.zone.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.liste = ttk.Frame(self.zone)
        self.zone.create_window((0, 0), window=self.liste, anchor="nw", tags="liste")
        self.liste.bind("<Configure>", lambda _e: self.zone.configure(scrollregion=self.zone.bbox("all")))
        self.zone.bind("<Configure>", lambda e: self.zone.itemconfigure("liste", width=e.width))
        droite = ttk.LabelFrame(corps, text=" Aperçu ", padding=6)
        droite.grid(row=0, column=1, sticky="nsew")
        self.canvas = tk.Canvas(droite, bg="#e8eaed", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.lbl_info = ttk.Label(droite, text="")
        self.lbl_info.pack(fill="x", pady=(6, 0))
        actions = ttk.Frame(p)
        actions.pack(fill="x", padx=12, pady=4)
        ttk.Button(actions, text="Convertir en texte", command=self._convertir).pack(side="left")
        ttk.Button(actions, text="Effacer la sélection", command=self._effacer).pack(side="left", padx=8)
        journal = ttk.LabelFrame(p, text=" Journal de conversion intelligente ", padding=4)
        journal.pack(fill="x", padx=12, pady=(0, 8))
        self.journal = tk.Text(journal, height=5, font=("Consolas", 9), wrap="word", bg="#fff")
        self.journal.pack(fill="x")
        self.journal.insert("1.0", "Seuls les PDF scannés et les PDF image sont listés. Les PDF avec du vrai texte sont écartés.\n")
        self.journal.configure(state="disabled")

    def _params(self) -> None:
        p = self.onglet_params
        bloc = ttk.LabelFrame(p, text=" Dossier cible du texte ", padding=12)
        bloc.pack(fill="x", padx=16, pady=16)
        ttk.Label(bloc, text="Chemin du dossier où seront enregistrés les textes :").pack(anchor="w")
        ligne = ttk.Frame(bloc)
        ligne.pack(fill="x", pady=6)
        self.var_cible = tk.StringVar(value=self.params.dossier_cible)
        self.entree = ttk.Entry(ligne, textvariable=self.var_cible)
        self.entree.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(ligne, text="Chemin courant", command=self._hellodoc).pack(side="left")
        self.var_sous = tk.BooleanVar(value=bool(self.params.parcourir_sous_dossiers))
        tk.Checkbutton(p, text="Parcourir les sous-dossiers", variable=self.var_sous, anchor="w").pack(anchor="w", padx=16, pady=8)
        ttk.Button(p, text="Enregistrer", command=self._sauver).pack(anchor="w", padx=16)

    def _log(self, texte: str) -> None:
        self.journal.configure(state="normal")
        self.journal.insert("end", texte + "\n")
        self.journal.see("end")
        self.journal.configure(state="disabled")

    def _hellodoc(self) -> None:
        self.var_cible.set(r"C:\Hellodoc\scans")
        self.entree.delete(0, "end")
        self.entree.insert(0, r"C:\Hellodoc\scans")

    def _sauver(self) -> None:
        self.params.dossier_cible = self.var_cible.get().strip()
        self.params.parcourir_sous_dossiers = bool(self.var_sous.get())
        self.params.sauvegarder()
        messagebox.showinfo(APP_TITRE, "Paramètres enregistrés.", parent=self)

    def _parcourir(self) -> None:
        from patches_ui import dialogue_explorateur
        d = dialogue_explorateur(self, "Dossier des PDF scannés", True, afficher_fichiers=True)
        if d:
            self._charger(Path(d))

    def _charger(self, path: Path) -> None:
        if not path.is_dir():
            messagebox.showwarning(APP_TITRE, "Choisissez un dossier de PDF scannés.", parent=self)
            return
        self.source_path = path
        self.lbl_source.configure(text=f"{path}   —   {path.name}")
        self.fichiers, ecartes = lister_scans(path, bool(self.var_sous.get()))
        for p in self.fichiers:
            self.vars_coche.setdefault(str(p), True)
        self._rafraichir()
        self._log(f"{len(self.fichiers)} PDF scanné(s) ou image. {ecartes} PDF avec du vrai texte écarté(s).")

    def _rafraichir(self) -> None:
        for enfant in self.liste.winfo_children():
            enfant.destroy()
        for p in self.fichiers:
            cle = str(p)
            var = tk.BooleanVar(value=self.vars_coche.get(cle, True))
            ligne = ttk.Frame(self.liste)
            ligne.pack(fill="x", pady=2)
            case = tk.Checkbutton(ligne, variable=var, command=lambda c=cle, v=var: self.vars_coche.__setitem__(c, bool(v.get())))
            case.pack(side="left")
            nom = tk.Label(ligne, text=p.name, font=("Segoe UI", 10), fg="#1f4e79", bg="#ffffff", cursor="hand2")
            nom.pack(side="left", padx=(4, 8))
            chemin = tk.Label(ligne, text=str(p), font=("Segoe UI", 8), fg="#6b7280", bg="#ffffff", cursor="hand2")
            chemin.pack(side="left")
            nom.bind("<Button-1>", lambda _e, fichier=p: self._apercu(fichier))
            chemin.bind("<Button-1>", lambda _e, fichier=p: self._apercu(fichier))
        self.zone.update_idletasks()
        self.zone.configure(scrollregion=self.zone.bbox("all"))

    def _apercu(self, path: Path) -> None:
        self.canvas.delete("all")
        self.apercu_img = None
        self.lbl_info.configure(text=path.name + "  —  " + str(path))
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 280)
        ch = max(self.canvas.winfo_height(), 220)
        try:
            im = apercu_pdf.charger(path, cw - 8, ch - 8)
            self.apercu_img = ImageTk.PhotoImage(im, master=self.canvas)
            self.canvas.create_image(cw // 2, ch // 2, image=self.apercu_img)
        except Exception as e:
            self.canvas.create_text(12, 12, anchor="nw", text="Aperçu impossible\n" + str(e), fill="#444", width=cw - 24)

    def _tout_cocher(self) -> None:
        for p in self.fichiers:
            self.vars_coche[str(p)] = True
        self._rafraichir()

    def _tout_decocher(self) -> None:
        for p in self.fichiers:
            self.vars_coche[str(p)] = False
        self._rafraichir()

    def _convertir(self) -> None:
        coches = [p for p in self.fichiers if self.vars_coche.get(str(p))]
        if not coches:
            messagebox.showinfo(APP_TITRE, "Aucun PDF scanné coché.", parent=self)
            return
        messagebox.showinfo(
            APP_TITRE,
            "La conversion intelligente vers texte n'est pas encore branchée.\n"
            f"{len(coches)} PDF scanné(s) sont prêts. L'OCR sera ajouté ensuite.",
            parent=self,
        )

    def _effacer(self) -> None:
        self.source_path = None
        self.fichiers = []
        self.vars_coche.clear()
        self.lbl_source.configure(text="(aucun dossier)")
        self.canvas.delete("all")
        self.apercu_img = None
        self.lbl_info.configure(text="")
        self._rafraichir()

    def _quitter(self) -> None:
        maitre = self.master
        self.destroy()
        if maitre is not None:
            try:
                maitre.deiconify()
                maitre.lift()
            except tk.TclError:
                pass
