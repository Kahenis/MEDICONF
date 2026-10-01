# -*- coding: utf-8 -*-
from __future__ import annotations
import os, tkinter as tk
from tkinter import ttk
COULEUR_FOND = "#eef2f6"
COULEUR_ACCENT = "#1f4e79"
CREDIT = "Cr\u00e9ation et D\u00e9veloppement par JF GUILARD"

class MenuDemarrage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MEDICONF")
        self.geometry("760x460")
        self.minsize(640, 380)
        self.configure(bg=COULEUR_FOND)
        ttk.Label(self, text="MEDICONF", font=("Segoe UI", 22, "bold"), background=COULEUR_FOND, foreground=COULEUR_ACCENT).pack(pady=(28, 4))
        ttk.Label(self, text=CREDIT, background=COULEUR_FOND).pack(pady=(0, 2))
        ttk.Label(self, text="Choisissez le module a lancer", background=COULEUR_FOND).pack(pady=(0, 22))
        zone = ttk.Frame(self)
        zone.pack(fill="both", expand=True, padx=36, pady=(0, 28))
        zone.columnconfigure(0, weight=1); zone.columnconfigure(1, weight=1); zone.rowconfigure(0, weight=1)
        self._gros(zone, 0, "Conversion en PDF\nvers HelloDoc", "Partie 1", "#1f4e79", self._ouvrir_pdf)
        self._gros(zone, 1, "Conversion intelligente\nPDF vers texte", "Partie 2", "#0d7377", self._ouvrir_texte)
        self.protocol("WM_DELETE_WINDOW", self._fermer_tout)
    def _gros(self, parent, col, titre, sous, couleur, cmd):
        cadre = tk.Frame(parent, bg=couleur)
        cadre.grid(row=0, column=col, sticky="nsew", padx=10, pady=8)
        tk.Button(cadre, text=titre, font=("Segoe UI", 14, "bold"), fg="#fff", bg=couleur, relief="flat", command=cmd).pack(fill="both", expand=True)
        tk.Label(cadre, text=sous, fg="#e8eef5", bg=couleur).pack(pady=(0, 10))
    def _fermer_tout(self):
        try: self.destroy()
        except tk.TclError: pass
        os._exit(0)
    def _ouvrir_pdf(self):
        from patches_ui import appliquer, brancher_memoire
        from app import ConvertisseurApp
        appliquer(ConvertisseurApp)
        self.withdraw()
        try: fen = ConvertisseurApp(self)
        except TypeError: fen = ConvertisseurApp()
        brancher_memoire(fen)
    def _ouvrir_texte(self):
        from reception import ReceptionApp
        self.withdraw()
        ReceptionApp(self)
