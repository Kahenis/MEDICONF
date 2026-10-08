# -*- coding: utf-8 -*-
"""Convertisseur PDF — images et documents bureautique vers PDF."""
from __future__ import annotations

import hashlib
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import apercu
import apercu_doc
import apercu_image
import apercu_pdf
import themes
import scan_source
from conversion import (
    EXTENSIONS_OK,
    convertir_fichier,
    est_document,
    est_image,
    nom_pdf_cible,
)
from parametres import Parametres

APP_TITRE = "MEDICONF - Convertisseur PDF Pour hellodoc - Par JF Guilard"
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
        self.etats_fichier: dict[str, str] = {}
        self.labels_nom: dict[str, tk.Label] = {}
        self.apercu_img = None
        self.conversion_en_cours = False
        self.annuler_conversion = False
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
        themes.appliquer(self)

    def _construire(self) -> None:
        ttk.Label(self, text=APP_TITRE, style="Titre.TLabel").pack(anchor="w", padx=16, pady=(12, 4))
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.notebook = nb
        self.onglet_principal = ttk.Frame(nb)
        self.onglet_params = ttk.Frame(nb)
        nb.add(self.onglet_principal, text="  Conversion  ")
        nb.add(self.onglet_params, text="  Paramètres  ")
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self._appliquer_cases())
        self._onglet_principal()
        self._onglet_params()
        self._recharger_params()

    def _recharger_params(self) -> None:
        from parametres import fichier_config
        self.params = Parametres.charger()
        chemin = self.params.dossier_cible
        self.var_cible.set(chemin)
        try:
            self.entree_cible.delete(0, "end")
            if chemin:
                self.entree_cible.insert(0, chemin)
        except Exception:
            pass
        self.var_sous.set(1 if self.params.parcourir_sous_dossiers else 0)
        self.var_arbo.set(1 if self.params.conserver_arborescence else 0)
        self.var_comp.set(1 if self.params.compression else 0)
        self.var_doublons.set(1 if self.params.masquer_identiques else 0)
        self._cases = {
            "sous": bool(self.params.parcourir_sous_dossiers),
            "arbo": bool(self.params.conserver_arborescence),
            "comp": bool(self.params.compression),
            "doublons": bool(self.params.masquer_identiques),
        }
        self.after(150, self._appliquer_cases)
        self.var_qualite.set(int(self.params.qualite_compression or 75))
        self.scale_qualite.set(self.var_qualite.get())
        self.lbl_qualite.configure(text=f"{self.var_qualite.get()} %")
        self.var_conflit.set(self.params.conflit or "renommer")
        themes.appliquer(self)
        self._appliquer_cases()
        self._afficher_chemin_enregistre()
        self._log("Paramètres repris : sous-dossiers=" + ("oui" if self._cases["sous"] else "non") + ", arborescence=" + ("oui" if self._cases["arbo"] else "non") + ", compression=" + ("oui" if self._cases["comp"] else "non"))

    def _noter_case(self, cle) -> None:
        self._cases[cle] = not self._cases.get(cle, False)
        if cle == "sous":
            self.var_sous.set(1 if self._cases[cle] else 0)
            self._basculer_sous_dossiers()
        if cle == "doublons":
            self.var_doublons.set(1 if self._cases[cle] else 0)
            self.after(80, self._rafraichir_liste)

    def _appliquer_cases(self) -> None:
        for case, cle, var in (
            (self.case_sous, "sous", self.var_sous),
            (self.case_arbo, "arbo", self.var_arbo),
            (self.case_comp, "comp", self.var_comp),
            (self.case_doublons, "doublons", self.var_doublons),
        ):
            actif = bool(self._cases.get(cle))
            var.set(1 if actif else 0)
            try:
                case.configure(command="")
                if actif:
                    case.select()
                else:
                    case.deselect()
            except Exception:
                pass
        self.case_sous.configure(command=lambda: self._noter_case("sous"))
        self.case_arbo.configure(command=lambda: self._noter_case("arbo"))
        self.case_comp.configure(command=lambda: self._noter_case("comp"))
        self.case_doublons.configure(command=lambda: self._noter_case("doublons"))
        self._marquer_radios()

    def _marquer_radios(self) -> None:
        def walk(w):
            for enfant in w.winfo_children():
                try:
                    if enfant.winfo_class() == "TRadiobutton" and str(enfant.cget("value")) == self.var_conflit.get():
                        enfant.invoke()
                except Exception:
                    pass
                walk(enfant)
        walk(self.onglet_params)

    def _onglet_params(self) -> None:
        p = self.onglet_params
        bloc = ttk.LabelFrame(p, text=" Dossier cible ", padding=12)
        bloc.pack(fill="x", padx=16, pady=16)
        self.var_cible = tk.StringVar(value=self.params.dossier_cible)
        ttk.Label(bloc, text="Chemin du dossier o\u00f9 seront enregistr\u00e9s les PDF :").pack(anchor="w")
        ligne = ttk.Frame(bloc)
        ligne.pack(fill="x", pady=6)
        self.entree_cible = ttk.Entry(ligne, textvariable=self.var_cible)
        self.entree_cible.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(ligne, text="Parcourir\u2026", command=self._parcourir_cible).pack(side="left", padx=(0, 8))
        ttk.Button(ligne, text="Choisir ce dossier", command=self._valider_cible).pack(side="left")
        self.lbl_chemin_enregistre = ttk.Label(bloc, text="Chemin actuel de destination : (aucun)", style="Info.TLabel")
        self.lbl_chemin_enregistre.pack(anchor="w", pady=(2, 6))
        hello = ttk.Frame(bloc)
        hello.pack(fill="x", pady=(4, 0))
        ttk.Label(hello, text="Boite de réception Hellodoc de l'utilisateur").pack(side="left")
        ttk.Button(hello, text="Chemin courant", command=self._chemin_hellodoc).pack(side="left", padx=12)
        milieu = ttk.Frame(p)
        milieu.pack(fill="x", padx=16, pady=8)
        milieu.columnconfigure(0, weight=1)
        milieu.columnconfigure(1, weight=1)
        opts = ttk.LabelFrame(milieu, text=" Options de parcours et de conversion ", padding=12)
        opts.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.var_sous = tk.IntVar(value=1 if self.params.parcourir_sous_dossiers else 0)
        self.case_sous = tk.Checkbutton(opts, text="Parcourir les sous-dossiers", variable=self.var_sous, onvalue=1, offvalue=0, anchor="w", command=lambda: self._noter_case("sous"))
        self.case_sous.pack(fill="x", pady=3)
        self.var_arbo = tk.IntVar(value=1 if self.params.conserver_arborescence else 0)
        self.case_arbo = tk.Checkbutton(opts, text="Conserver l'arborescence dans le dossier cible", variable=self.var_arbo, onvalue=1, offvalue=0, anchor="w", command=lambda: self._noter_case("arbo"))
        self.case_arbo.pack(fill="x", pady=3)
        self.var_comp = tk.IntVar(value=1 if self.params.compression else 0)
        self.case_comp = tk.Checkbutton(opts, text="Compresser les images avant le PDF", variable=self.var_comp, onvalue=1, offvalue=0, anchor="w", command=lambda: self._noter_case("comp"))
        self.case_comp.pack(fill="x", pady=3)
        self.var_doublons = tk.IntVar(value=1 if self.params.masquer_identiques else 0)
        self.case_doublons = tk.Checkbutton(opts, text="Masquer les fichiers 100 % identiques", variable=self.var_doublons, onvalue=1, offvalue=0, anchor="w", command=lambda: self._noter_case("doublons"))
        self.case_doublons.pack(fill="x", pady=3)
        self._cases = {
            "sous": bool(self.params.parcourir_sous_dossiers),
            "arbo": bool(self.params.conserver_arborescence),
            "comp": bool(self.params.compression),
            "doublons": bool(self.params.masquer_identiques),
        }
        qligne = ttk.Frame(opts)
        qligne.pack(fill="x", pady=8)
        ttk.Label(qligne, text="Qualité de compression :").pack(side="left")
        self.var_qualite = tk.IntVar(value=self.params.qualite_compression)
        self.lbl_qualite = ttk.Label(qligne, text=f"{self.var_qualite.get()} %")
        self.lbl_qualite.pack(side="right")
        self.scale_qualite = ttk.Scale(opts, from_=40, to=95, orient="horizontal", command=self._chg_qualite)
        self.scale_qualite.set(self.params.qualite_compression)
        self.scale_qualite.pack(fill="x", pady=(0, 8))
        conflit = ttk.LabelFrame(milieu, text=" Si un PDF du même nom existe déjà ", padding=12)
        conflit.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.var_conflit = tk.StringVar(value=self.params.conflit or "renommer")
        for val, txt in (
            ("renommer", "Renommer automatiquement"),
            ("ecraser", "Écraser le fichier existant"),
            ("demander", "Demander à chaque fois"),
        ):
            ttk.Radiobutton(conflit, text=txt, value=val, variable=self.var_conflit).pack(anchor="w", pady=2)
        ttk.Button(p, text="Enregistrer", command=self._sauver_params).pack(anchor="w", padx=16, pady=8)

    def _chemin_hellodoc(self) -> None:
        self.var_cible.set(r"C:\Hellodoc\scans")
        try:
            self.entree_cible.delete(0, "end")
            self.entree_cible.insert(0, r"C:\Hellodoc\scans")
        except Exception:
            pass

    def _chg_qualite(self, _evt=None) -> None:
        v = int(float(self.scale_qualite.get()))
        self.var_qualite.set(v)
        self.lbl_qualite.configure(text=f"{v} %")

    def _ecrire_cible(self, chemin: str) -> None:
        chemin = (chemin or "").strip().strip('"')
        if not chemin:
            return
        self.var_cible.set(chemin)
        try:
            self.entree_cible.delete(0, "end")
            self.entree_cible.insert(0, chemin)
        except Exception:
            pass
        self.params.dossier_cible = chemin
        self._log("Dossier cible proposé : " + chemin)

    def _parcourir_cible(self) -> None:
        from patches_ui import dialogue_explorateur
        d = dialogue_explorateur(self, "Choisir le dossier cible", True, afficher_fichiers=True)
        if not d:
            self._boite(messagebox.showwarning, "L'explorateur n'a pas renvoyé de chemin.")
            return
        self._ecrire_cible(d)

    def _valider_cible(self) -> None:
        d = self.var_cible.get().strip().strip('"')
        if not d:
            self._boite(messagebox.showwarning, "saisie vide")
            return
        self.var_cible.set(d)
        try:
            self.entree_cible.delete(0, "end")
            self.entree_cible.insert(0, d)
        except Exception:
            pass
        self.params.dossier_cible = d
        try:
            self.params.sauvegarder()
        except Exception as e:
            self._log("Chemin non enregistré : " + str(e), erreur=True)
            return
        self._afficher_chemin_enregistre()
        self._log("Chemin de destination enregistré : " + d)

    def _basculer_sous_dossiers(self) -> None:
        self.after(80, self._appliquer_sous_dossiers)

    def _appliquer_sous_dossiers(self) -> None:
        actif = self._sous_dossiers_demandes()
        if getattr(self, "source_path", None) and Path(self.source_path).is_dir():
            self.fichiers = self._scanner(self.source_path)
            self._rafraichir_liste()
            self._log(str(len(self.fichiers)) + " fichier(s), sous-dossiers : " + ("oui" if actif else "non"))

    def _sauver_params(self, afficher: bool = True) -> None:
        self.params.dossier_cible = self.var_cible.get().strip()
        self.params.parcourir_sous_dossiers = bool(self._cases.get("sous"))
        self.params.compression = bool(self._cases.get("comp"))
        self.params.qualite_compression = int(float(self.scale_qualite.get()))
        self.params.conserver_arborescence = bool(self._cases.get("arbo"))
        self.params.masquer_identiques = bool(self._cases.get("doublons"))
        self.params.conflit = self.var_conflit.get()
        try:
            self.params.sauvegarder()
            from parametres import fichier_config
            self._log(
                "Enregistré : sous-dossiers=" + ("oui" if self.params.parcourir_sous_dossiers else "non")
                + ", arborescence=" + ("oui" if self.params.conserver_arborescence else "non")
                + ", compression=" + ("oui" if self.params.compression else "non")
                + ", identiques masqués=" + ("oui" if self.params.masquer_identiques else "non")
                + " — " + str(fichier_config())
            )
            if afficher:
                self._boite(messagebox.showinfo, "Paramètres enregistrés.\nSous-dossiers : " + ("oui" if self.params.parcourir_sous_dossiers else "non") + "\nArborescence : " + ("oui" if self.params.conserver_arborescence else "non") + "\nCompression : " + ("oui" if self.params.compression else "non"))
            self._afficher_chemin_enregistre()
        except Exception as e:
            self._log("Paramètres non enregistrés : " + str(e), erreur=True)

    def _onglet_principal(self) -> None:
        p = self.onglet_principal
        haut = ttk.Frame(p)
        haut.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(haut, text="Source :").pack(side="left")
        self.lbl_source = ttk.Label(haut, text="(aucun fichier ni dossier)", style="Info.TLabel")
        self.lbl_source.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(haut, text="Parcourir\u2026", command=self._parcourir_source).pack(side="left", padx=4)
        ttk.Button(haut, text="S\u00e9lectionner ce dossier source", command=self._choisir_dossier_source).pack(side="left")
        cases = ttk.Frame(p)
        cases.pack(anchor="w", padx=12, pady=(4, 0))
        ttk.Button(cases, text="Tout cocher", command=self._tout_cocher).pack(side="left")
        ttk.Button(cases, text="Tout décocher", command=self._tout_decocher).pack(side="left", padx=8)
        corps = ttk.Frame(p)
        corps.pack(fill="both", expand=True, padx=12, pady=6)
        corps.columnconfigure(0, weight=1, uniform="moitie")
        corps.columnconfigure(1, weight=1, uniform="moitie")
        corps.rowconfigure(0, weight=1)
        gauche = ttk.LabelFrame(corps, text=" Fichiers source ", padding=6)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        gauche.rowconfigure(0, weight=1)
        gauche.columnconfigure(0, weight=1)
        self.zone_drop = tk.Canvas(gauche, bg=COULEUR_ZONE, highlightthickness=0)
        sb = ttk.Scrollbar(gauche, orient="vertical", command=self.zone_drop.yview)
        self.zone_drop.configure(yscrollcommand=sb.set)
        self.zone_drop.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.liste_frame = ttk.Frame(self.zone_drop)
        self.zone_drop.create_window((0, 0), window=self.liste_frame, anchor="nw", tags="liste")
        self.liste_frame.bind("<Configure>", lambda _e: self.zone_drop.configure(scrollregion=self.zone_drop.bbox("all")))
        self.zone_drop.bind("<Configure>", lambda e: self.zone_drop.itemconfigure("liste", width=e.width))
        self.zone_drop.bind("<MouseWheel>", self._molette_liste)
        self.liste_frame.bind("<MouseWheel>", self._molette_liste)
        droite = ttk.LabelFrame(corps, text=" Aper\u00e7u ", padding=6)
        droite.grid(row=0, column=1, sticky="nsew")
        self.cadre_apercu = droite
        zoom = ttk.Frame(droite)
        zoom.pack(fill="x")
        ttk.Button(zoom, text=" − ", width=3, command=self._zoom_moins).pack(side="left")
        ttk.Button(zoom, text=" + ", width=3, command=self._zoom_plus).pack(side="left", padx=4)
        self.lbl_zoom = ttk.Label(zoom, text="100 %")
        self.lbl_zoom.pack(side="left", padx=6)
        self._zoom = 1.0
        self._apercu_chemin = ""
        self.canvas_apercu = tk.Canvas(droite, bg="#e8eaed", highlightthickness=0)
        self.canvas_apercu.pack(fill="both", expand=True)
        self.lbl_image = tk.Label(self.canvas_apercu, bg="#e8eaed")
        self.lbl_apercu_info = ttk.Label(droite, text="", wraplength=460)
        self.lbl_apercu_info.pack(fill="x", pady=(6, 0))
        self.canvas_apercu.bind("<Configure>", self._largeur_apercu)
        self.canvas_apercu.bind("<MouseWheel>", self._molette_apercu)
        self.canvas_apercu.bind("<ButtonPress-1>", self._apercu_saisir)
        self.canvas_apercu.bind("<B1-Motion>", self._apercu_deplacer)
        self.canvas_apercu.configure(cursor="fleur")
        actions = ttk.Frame(p)
        actions.pack(fill="x", padx=12, pady=4)
        self.btn_convertir = ttk.Button(actions, text="Convertir", command=self._tout_convertir)
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
        self.journal.tag_configure("erreur", font=("Consolas", 9, "bold"), foreground="#b91c1c")
        self.journal.configure(state="disabled")
        self._log("Parcourir un fichier ou s\u00e9lectionner un dossier source pour commencer.")

    def _largeur_apercu(self, evt=None) -> None:
        try:
            self.lbl_apercu_info.configure(wraplength=max(evt.width - 12, 200))
        except Exception:
            pass

    def _parcourir_source(self) -> None:
        if self._boite(messagebox.askquestion, "Oui = dossier\nNon = fichier unique", icon="question") == "yes":
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
            self._boite(messagebox.showerror, "Chemin introuvable.")
            return
        self.source_path = path
        if path.is_file():
            self.lbl_source.configure(text=f"{path.parent}   —   {path.name}")
            self.fichiers = [path]
            self._rafraichir_liste()
            return
        self.lbl_source.configure(text=f"{path}   —   {path.name}")
        self.fichiers = self._scanner(path)
        self._rafraichir_liste()
        try:
            self.btn_convertir.configure(state="normal")
            self.conversion_en_cours = False
        except Exception:
            pass
        self._log("Source : " + str(path) + " — " + str(len(self.fichiers)) + " fichier(s), sous-dossiers : " + ("oui" if self._sous_dossiers_demandes() else "non"))

    def _sous_dossiers_demandes(self) -> bool:
        return bool(self.var_sous.get())

    def _scanner(self, racine: Path) -> list[Path]:
        return scan_source.lister(racine, self._sous_dossiers_demandes())

    def _visible(self) -> list[Path]:
        if not self._cases.get("doublons"):
            return list(self.fichiers)
        return self._sans_doublons(self.fichiers)

    def _sans_doublons(self, fichiers: list[Path]) -> list[Path]:
        vus = {}
        gardes = []
        masques = 0
        for p in fichiers:
            try:
                taille = p.stat().st_size
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for bloc in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(bloc)
                cle = (taille, h.hexdigest())
            except Exception:
                gardes.append(p)
                continue
            if cle in vus:
                masques += 1
                continue
            vus[cle] = p
            gardes.append(p)
        if masques:
            self._log(str(masques) + " fichier(s) identique(s) masqué(s)")
        return gardes

    def _libelle(self, p: Path) -> str:
        return p.name

    def _rafraichir_liste(self) -> None:
        for enfant in self.liste_frame.winfo_children():
            enfant.destroy()
        self._index_visible = list(self._visible())
        for p in self._index_visible:
            cle = str(p)
            actuel = self.vars_coche.get(cle, False)
            if not isinstance(actuel, bool):
                try:
                    actuel = bool(actuel.get())
                except Exception:
                    actuel = True
            var = tk.BooleanVar(value=actuel)
            self.vars_coche[cle] = var
            ligne = tk.Frame(self.liste_frame, bg="#ffffff")
            ligne.pack(fill="x", anchor="w", pady=1)
            case = ttk.Checkbutton(ligne, variable=var)
            case.pack(side="left")
            case._chemin_source = cle
            case.bind("<ButtonRelease-1>", lambda _e, c=cle: self.after(60, lambda: self._lire_case(c)))
            couleur = {"ok": "#15803d", "erreur": "#b91c1c"}.get(self.etats_fichier.get(cle, ""), "#1f4e79")
            fond = "#dbeafe" if cle == getattr(self, "_apercu_chemin", "") else "#ffffff"
            ligne.configure(bg=fond)
            nom = tk.Label(ligne, text=p.name, font=("Segoe UI", 10), fg=couleur, bg=fond, cursor="hand2")
            nom.pack(side="left", padx=(4, 8))
            self.labels_nom[cle] = nom
            chemin_lbl = tk.Label(ligne, text=str(p), font=("Segoe UI", 8), fg="#6b7280", bg=fond, cursor="hand2")
            chemin_lbl.pack(side="left")
            nom._chemin_source = str(p)
            chemin_lbl._chemin_source = str(p)
            ligne._chemin_source = str(p)
            for widget in (ligne, nom, chemin_lbl):
                widget.bind("<Button-1>", self._clic_nom_fichier)
                widget.bind("<MouseWheel>", self._molette_liste)
            try:
                case.state(["selected"] if actuel else ["!selected"])
            except Exception:
                pass
        self.zone_drop.update_idletasks()
        self.zone_drop.configure(scrollregion=self.zone_drop.bbox("all"))
        self._log(str(len(self._index_visible)) + " fichier(s) affiché(s)" + (" — sous-dossiers" if self.var_sous.get() else ""))

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

    def _apercu_saisir(self, event) -> None:
        self.canvas_apercu.scan_mark(event.x, event.y)

    def _apercu_deplacer(self, event) -> None:
        self.canvas_apercu.scan_dragto(event.x, event.y, gain=1)

    def _molette_apercu(self, event) -> str:
        pas = -1 if event.delta > 0 else 1
        self.canvas_apercu.yview_scroll(pas, "units")
        return "break"

    def _molette_liste(self, event) -> str:
        pas = -1 if event.delta > 0 else 1
        self.zone_drop.yview_scroll(pas, "units")
        return "break"

    def _zoom_plus(self) -> None:
        self._zoom = min(3.0, round(self._zoom + 0.25, 2))
        self._reafficher_apercu()

    def _zoom_moins(self) -> None:
        self._zoom = max(0.5, round(self._zoom - 0.25, 2))
        self._reafficher_apercu()

    def _reafficher_apercu(self) -> None:
        self.lbl_zoom.configure(text=f"{int(self._zoom * 100)} %")
        if self._apercu_chemin:
            self._afficher_apercu(Path(self._apercu_chemin), garder_zoom=True)

    def _clic_nom_fichier(self, event) -> None:
        chemin = getattr(event.widget, "_chemin_source", "")
        if chemin:
            self._afficher_apercu(Path(chemin))

    def _afficher_apercu(self, path: Path, garder_zoom: bool = False) -> None:
        path = Path(path)
        if not garder_zoom:
            self._zoom = 1.0
            self.lbl_zoom.configure(text="100 %")
        self._apercu_chemin = str(path)
        for enfant in self.liste_frame.winfo_children():
            cle = getattr(enfant, "_chemin_source", "")
            fond = "#dbeafe" if cle == self._apercu_chemin else "#ffffff"
            try:
                enfant.configure(bg=fond)
            except Exception:
                pass
            for widget in enfant.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.configure(bg=fond)
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text=path.name + "  —  " + str(path))
        self.canvas_apercu.update_idletasks()
        cw = max(self.cadre_apercu.winfo_width() - 16, self.winfo_width() // 2 - 24, 280)
        ch = max(self.cadre_apercu.winfo_height() - 48, self.winfo_height() // 2 - 56, 200)
        cw = int(cw * self._zoom)
        ch = int(ch * self._zoom)
        if apercu_image.est_image(path):
            try:
                im = apercu_image.charger(path, cw - 16, ch - 16)
                self.apercu_img = ImageTk.PhotoImage(im, master=self.canvas_apercu)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
                self.canvas_apercu.configure(scrollregion=(0, 0, cw, ch))
            except Exception as e:
                self.canvas_apercu.create_text(12, 12, anchor="nw", text="Aperçu impossible\n" + str(e), fill="#444", width=cw - 24)
            return
        if apercu_doc.est_document(path):
            try:
                im = apercu_doc.charger(path, cw - 8, ch - 8)
                self.apercu_img = ImageTk.PhotoImage(im, master=self.canvas_apercu)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
                self.canvas_apercu.configure(scrollregion=(0, 0, cw, ch))
            except Exception as e:
                self.canvas_apercu.create_text(12, 12, anchor="nw", text="Aperçu impossible\n" + str(e), fill="#444", width=cw - 24)
            return
        if apercu_pdf.est_pdf(path):
            try:
                im = apercu_pdf.charger(path, cw - 8, ch - 8)
                self.apercu_img = ImageTk.PhotoImage(im, master=self.canvas_apercu)
                self.canvas_apercu.create_image(cw // 2, ch // 2, image=self.apercu_img)
                self.canvas_apercu.configure(scrollregion=(0, 0, cw, ch))
            except Exception as e:
                self.canvas_apercu.create_text(12, 12, anchor="nw", text="Aperçu impossible\n" + str(e), fill="#444", width=cw - 24)
            return
        self.canvas_apercu.create_text(16, 16, anchor="nw", text="Aperçu pas encore disponible\npour ce type de fichier.", fill="#444")

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
        for p in self.fichiers:
            self.vars_coche[str(p)] = True
        self._rafraichir_liste()

    def _tout_decocher(self) -> None:
        for p in self.fichiers:
            self.vars_coche[str(p)] = False
        self._rafraichir_liste()

    def _lire_case(self, cle: str) -> None:
        for enfant in self.liste_frame.winfo_children():
            for case in enfant.winfo_children():
                if getattr(case, "_chemin_source", "") == cle:
                    try:
                        self.vars_coche[cle] = bool(case.instate(["selected"]))
                    except Exception:
                        pass
                    return

    def _selectionnes(self) -> list[Path]:
        choisis = []
        for p in self._visible():
            cle = str(p)
            coche = False
            for enfant in self.liste_frame.winfo_children():
                for case in enfant.winfo_children():
                    if getattr(case, "_chemin_source", "") == cle:
                        try:
                            coche = bool(case.instate(["selected"]))
                        except Exception:
                            coche = self._coche(cle)
                        break
            self.vars_coche[cle] = coche
            if coche:
                choisis.append(p)
        return choisis

    def _cible_ok(self) -> Path | None:
        d = self.var_cible.get().strip() or self.params.dossier_cible
        if not d:
            self._boite(messagebox.showwarning, "Définissez un dossier cible dans Paramètres, puis « Choisir ce dossier ».")
            return None
        p = Path(d)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._boite(messagebox.showerror, f"Dossier cible invalide :\n{e}")
            return None
        return p

    def _resoudre_conflit(self, dest: Path, source: Path) -> Path | None:
        if not dest.exists() or self.var_conflit.get() != "demander":
            return dest
        r = self._boite(messagebox.askyesnocancel, f"Le fichier existe déjà :\n{dest.name}\n\nOui = écraser\nNon = renommer\nAnnuler = ignorer")
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
            self._boite(messagebox.showinfo, f"PDF enregistré :\n{dest2}")
        except Exception as e:
            self._log(f"ERREUR  {source.name} : {e}")
            self._boite(messagebox.showerror, f"Conversion impossible :\n{e}")

    def _marquer(self, source: Path, etat: str) -> None:
        cle = str(source)
        self.etats_fichier[cle] = etat
        label = self.labels_nom.get(cle)
        if label is not None:
            try:
                label.configure(fg="#15803d" if etat == "ok" else "#b91c1c")
            except Exception:
                pass

    def _afficher_chemin_enregistre(self) -> None:
        try:
            chemin = Parametres.charger().dossier_cible or "(aucun chemin enregistré)"
            self.lbl_chemin_enregistre.configure(text="Chemin actuel de destination : " + chemin)
        except Exception:
            pass

    def _ancre_dialogue(self) -> tk.Toplevel:
        self.update_idletasks()
        x = self.winfo_rootx() + max(self.winfo_width(), 200) // 2
        y = self.winfo_rooty() + max(self.winfo_height(), 160) // 2
        ancre = tk.Toplevel(self)
        ancre.overrideredirect(True)
        ancre.geometry(f"1x1+{x}+{y}")
        try:
            ancre.attributes("-alpha", 0.0)
        except tk.TclError:
            ancre.withdraw()
        ancre.update_idletasks()
        return ancre

    def _centrer(self, fen: tk.Toplevel, largeur: int, hauteur: int) -> None:
        self.update_idletasks()
        x = self.winfo_rootx() + max(self.winfo_width() - largeur, 0) // 2
        y = self.winfo_rooty() + max(self.winfo_height() - hauteur, 0) // 2
        fen.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    def _boite(self, fonction, texte: str, **kw):
        ancre = self._ancre_dialogue()
        try:
            return fonction(APP_TITRE, texte, parent=ancre, **kw)
        finally:
            try:
                ancre.destroy()
            except tk.TclError:
                pass

    def _decocher_converti(self, source: Path) -> None:
        cle = str(source)
        actuel = self.vars_coche.get(cle)
        if hasattr(actuel, "set"):
            actuel.set(False)
        self.vars_coche[cle] = False
        for enfant in self.liste_frame.winfo_children():
            for case in enfant.winfo_children():
                if getattr(case, "_chemin_source", "") == cle:
                    try:
                        case.state(["!selected"])
                    except Exception:
                        pass
                    return

    def _ouvrir_parametres(self) -> None:
        try:
            self.notebook.select(self.onglet_params)
        except Exception:
            pass
        self._log("Choisissez un dossier cible dans Paramètres.")

    def _tout_convertir(self) -> None:
        if self.conversion_en_cours:
            return
        cible_txt = self.var_cible.get().strip() or self.params.dossier_cible
        if not cible_txt:
            self._ouvrir_parametres()
            return
        fichiers = self._selectionnes()
        if not fichiers:
            self._boite(messagebox.showinfo, "Aucun fichier coché.")
            return
        cible = self._cible_ok()
        if cible is None:
            self._ouvrir_parametres()
            return
        if not self._boite(messagebox.askyesno, f"Convertir {len(fichiers)} fichier(s) vers :\n{cible} ?"):
            return
        self._sauver_params(afficher=False)
        self.annuler_conversion = False
        self.conversion_en_cours = True
        self.btn_convertir.configure(state="disabled")
        self.progress.configure(maximum=len(fichiers), value=0)
        self._popup_conversion()
        file_ui: queue.Queue = queue.Queue()
        racine = self.source_path if self.source_path and self.source_path.is_dir() else None
        compression = bool(self.var_comp.get())
        qualite = int(self.var_qualite.get())
        arbo = bool(self.var_arbo.get())
        conflit = self.var_conflit.get()

        def travail() -> None:
            ok = ko = 0
            for i, source in enumerate(fichiers, 1):
                if self.annuler_conversion:
                    file_ui.put(("stop", ok, ko))
                    return
                file_ui.put(("courant", source.name, i, len(fichiers)))
                try:
                    dest = nom_pdf_cible(source, cible, racine, arbo, "renommer" if conflit == "demander" else conflit)
                    warn = convertir_fichier(source, dest, compression, qualite)
                    ok += 1
                    file_ui.put(("ok", source, dest, warn))
                except Exception as e:
                    ko += 1
                    file_ui.put(("err", source, str(e)))
            file_ui.put(("fin", ok, ko))

        def pompe() -> None:
            termine = False
            try:
                while True:
                    ev = file_ui.get_nowait()
                    if ev[0] == "courant":
                        self.lbl_conv_fichier.configure(text=f"{ev[2]} / {ev[3]}\n{ev[1]}")
                    elif ev[0] == "ok":
                        source, dest, warn = ev[1], ev[2], ev[3]
                        msg = f"OK  {source.name}  →  {dest}"
                        if source.suffix.lower() == ".pdf":
                            msg += "  (copie seule)"
                        if warn:
                            msg += f"  ({warn})"
                        self._log(msg)
                        self._marquer(source, "ok")
                        self._decocher_converti(source)
                        self.progress.configure(value=self.progress["value"] + 1)
                    elif ev[0] == "err":
                        self._log(f"ERREUR  {ev[1].name} : {ev[2]}", erreur=True)
                        self._marquer(ev[1], "erreur")
                        self.progress.configure(value=self.progress["value"] + 1)
                    elif ev[0] == "stop":
                        self._log(f"Conversion annulée : {ev[1]} réussi(s), {ev[2]} échec(s).")
                        termine = True
                    elif ev[0] == "fin":
                        self._log(f"Terminé : {ev[1]} réussi(s), {ev[2]} échec(s).")
                        termine = True
            except queue.Empty:
                pass
            if termine:
                self.conversion_en_cours = False
                self.btn_convertir.configure(state="normal")
                try:
                    self.popup_conv.destroy()
                except Exception:
                    pass
                return
            self.after(80, pompe)

        threading.Thread(target=travail, daemon=True).start()
        self.after(80, pompe)

    def _popup_conversion(self) -> None:
        pop = tk.Toplevel(self)
        pop.title("Conversion en cours")
        pop.geometry("460x160")
        pop.transient(self)
        pop.resizable(False, False)
        self._centrer(pop, 460, 160)
        ttk.Label(pop, text="Fichier en cours :").pack(anchor="w", padx=16, pady=(14, 4))
        self.lbl_conv_fichier = ttk.Label(pop, text="Préparation…", wraplength=420)
        self.lbl_conv_fichier.pack(anchor="w", padx=16)
        ttk.Button(pop, text="Annuler", command=self._annuler_conversion).pack(pady=16)
        pop.protocol("WM_DELETE_WINDOW", self._annuler_conversion)
        self.popup_conv = pop

    def _annuler_conversion(self) -> None:
        self.annuler_conversion = True
        try:
            self.lbl_conv_fichier.configure(text="Arrêt demandé, fin du fichier en cours…")
        except Exception:
            pass

    def _effacer(self) -> None:
        self.source_path = None
        self.fichiers = []
        self.etats_fichier = {}
        self.labels_nom = {}
        self.lbl_source.configure(text="(aucun fichier ni dossier)")
        self._apercu_chemin = ""
        self._zoom = 1.0
        self._rafraichir_liste()
        self.canvas_apercu.delete("all")
        self.apercu_img = None
        self.lbl_apercu_info.configure(text="")
        self.progress.configure(value=0)
        self._log("S\u00e9lection effac\u00e9e.")

    def _ouvrir_cible(self) -> None:
        d = self.var_cible.get().strip() or self.params.dossier_cible
        if not d or not Path(d).is_dir():
            self._boite(messagebox.showwarning, "Aucun dossier cible valide.")
            return
        if sys.platform.startswith("win"):
            os.startfile(d)  # type: ignore
        elif sys.platform == "darwin":
            os.system(f'open "{d}"')
        else:
            os.system(f'xdg-open "{d}"')

    def _log(self, msg: str, erreur: bool = False) -> None:
        self.journal.configure(state="normal")
        if erreur:
            self.journal.insert("end", msg + "\n", "erreur")
        else:
            self.journal.insert("end", msg + "\n")
        self.journal.see("end")
        self.journal.configure(state="disabled")

    def _quitter(self) -> None:
        self.destroy()


def main() -> None:
    ConvertisseurApp().mainloop()


if __name__ == "__main__":
    main()
