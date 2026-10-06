# -*- coding: utf-8 -*-
from __future__ import annotations
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

COULEUR_FOND = "#f4f6f8"
COULEUR_ZONE = "#ffffff"
APP_TITRE = "MEDICONF"

def choisir_type_source(parent: tk.Tk) -> str | None:
    choix = {"v": None}
    win = tk.Toplevel(parent)
    win.title("Selection")
    win.transient(parent)
    win.resizable(False, False)
    win.configure(bg=COULEUR_FOND)
    ttk.Label(win, text="Selection d'un dossier ou d'un fichier ?", font=("Segoe UI", 12, "bold")).pack(padx=24, pady=(18, 12))
    btns = ttk.Frame(win)
    btns.pack(padx=24, pady=(0, 18))
    def setv(v: str) -> None:
        choix["v"] = v
        win.destroy()
    ttk.Button(btns, text="Dossier", command=lambda: setv("dossier")).pack(side="left", padx=8, ipadx=12)
    ttk.Button(btns, text="Fichier", command=lambda: setv("fichier")).pack(side="left", padx=8, ipadx=12)
    win.update_idletasks()
    parent.update_idletasks()
    largeur = max(win.winfo_reqwidth(), 360)
    hauteur = max(win.winfo_reqheight(), 110)
    x = parent.winfo_rootx() + max(parent.winfo_width() - largeur, 0) // 2
    y = parent.winfo_rooty() + max(parent.winfo_height() - hauteur, 0) // 2
    win.geometry(f"{largeur}x{hauteur}+{x}+{y}")
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.grab_set()
    parent.wait_window(win)
    return choix["v"]

def explorer_dossier(parent: tk.Tk, titre: str = "Selectionner un dossier") -> str | None:
    courant = tk.StringVar(value=str(Path.home()))
    choisi = {"v": None}
    win = tk.Toplevel(parent)
    win.title(titre)
    win.geometry("720x480")
    win.transient(parent)
    win.configure(bg=COULEUR_FOND)
    haut = ttk.Frame(win)
    haut.pack(fill="x", padx=10, pady=8)
    ttk.Label(haut, text="Dossier :").pack(side="left")
    ent = ttk.Entry(haut, textvariable=courant)
    ent.pack(side="left", fill="x", expand=True, padx=6)
    liste = tk.Listbox(win, font=("Segoe UI", 10), bg=COULEUR_ZONE)
    sb = ttk.Scrollbar(win, orient="vertical", command=liste.yview)
    liste.configure(yscrollcommand=sb.set)
    liste.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=4)
    sb.pack(side="left", fill="y", pady=4)
    def lister() -> None:
        liste.delete(0, "end")
        p = Path(courant.get())
        if not p.is_dir():
            liste.insert("end", "(chemin invalide)")
            return
        liste.insert("end", "..  (dossier parent)")
        try:
            enfants = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError as e:
            liste.insert("end", f"(erreur : {e})")
            return
        for enfant in enfants:
            if enfant.is_dir():
                liste.insert("end", f"[DIR]  {enfant.name}")
            elif enfant.is_file():
                extra = "  (PDF - copie seule)" if enfant.suffix.lower() == ".pdf" else ""
                liste.insert("end", f"[FIC]  {enfant.name}{extra}")
    def aller_parent() -> None:
        p = Path(courant.get())
        if p.parent != p:
            courant.set(str(p.parent))
            lister()
    def ouvrir_sel(_evt=None) -> None:
        sel = liste.curselection()
        if not sel:
            return
        texte = liste.get(sel[0])
        if texte.startswith(".."):
            aller_parent()
            return
        nom = texte.split("  ", 1)[-1].replace("  (PDF - copie seule)", "")
        cible = Path(courant.get()) / nom
        if cible.is_dir():
            courant.set(str(cible))
            lister()
    def valider() -> None:
        p = Path(courant.get())
        if p.is_dir():
            choisi["v"] = str(p)
            win.destroy()
        else:
            messagebox.showwarning(APP_TITRE, "Ce chemin n'est pas un dossier.", parent=win)
    bas = ttk.Frame(win)
    bas.pack(fill="x", padx=10, pady=8)
    ttk.Button(bas, text="Dossier parent", command=aller_parent).pack(side="left")
    ttk.Button(bas, text="Actualiser", command=lister).pack(side="left", padx=6)
    ttk.Button(bas, text="Annuler", command=win.destroy).pack(side="right")
    ttk.Button(bas, text="Choisir ce dossier", command=valider).pack(side="right", padx=8)
    liste.bind("<Double-Button-1>", ouvrir_sel)
    ent.bind("<Return>", lambda _e: lister())
    lister()
    win.grab_set()
    parent.wait_window(win)
    return choisi["v"]
