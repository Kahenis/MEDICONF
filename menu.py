# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk

COULEUR_FOND = "#eef2f6"
COULEUR_ACCENT = "#1f4e79"
COULEUR_BOUTON = "#1f4e79"
COULEUR_BOUTON2 = "#0d7377"
CREDIT = "Cr\u00e9ation et D\u00e9veloppement par JF GUILARD"

class MenuDemarrage(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MEDICONF")
        self.geometry("760x460")
        self.minsize(640, 380)
        self.configure(bg=COULEUR_FOND)
        ttk.Label(self, text="MEDICONF", font=("Segoe UI", 22, "bold"), background=COULEUR_FOND, foreground=COULEUR_ACCENT).pack(pady=(28, 4))
        ttk.Label(self, text=CREDIT, background=COULEUR_FOND, font=("Segoe UI", 10)).pack(pady=(0, 2))
        ttk.Label(self, text="Choisissez le module a lancer", background=COULEUR_FOND).pack(pady=(0, 22))
        zone = ttk.Frame(self)
        zone.pack(fill="both", expand=True, padx=36, pady=(0, 28))
        zone.columnconfigure(0, weight=1)
        zone.columnconfigure(1, weight=1)
        zone.rowconfigure(0, weight=1)
        self._gros_bouton(zone, 0, "Conversion en PDF\nvers HelloDoc", "Images et documents -> PDF", COULEUR_BOUTON, self._ouvrir_pdf)
        self._gros_bouton(zone, 1, "Conversion intelligente\nPDF vers texte", "PDF -> texte pour HelloDoc", COULEUR_BOUTON2, self._ouvrir_texte)
        self.protocol("WM_DELETE_WINDOW", self._fermer_tout)

    def _gros_bouton(self, parent, col, titre, sous, couleur, commande):
        cadre = tk.Frame(parent, bg=couleur)
        cadre.grid(row=0, column=col, sticky="nsew", padx=10, pady=8)
        tk.Button(cadre, text=titre, font=("Segoe UI", 14, "bold"), fg="#fff", bg=couleur, relief="flat", command=commande).pack(fill="both", expand=True)
        tk.Label(cadre, text=sous, font=("Segoe UI", 9), fg="#e8eef5", bg=couleur).pack(fill="x", pady=(0, 12))

    def _fermer_tout(self):
        try:
            self.destroy()
        except tk.TclError:
            pass
        os._exit(0)

    def _ouvrir_pdf(self):
        from patches_ui import appliquer
        from app import ConvertisseurApp
        appliquer(ConvertisseurApp)
        self.withdraw()
        try:
            fen = ConvertisseurApp(self)
        except TypeError:
            fen = ConvertisseurApp()
        ttk.Button(fen, text="Retour au menu", command=fen._quitter).pack(side="bottom", pady=6)
        fen.protocol("WM_DELETE_WINDOW", fen._quitter)

    def _ouvrir_texte(self):
        from reception import ReceptionApp
        self.withdraw()
        ReceptionApp(self)
