# -*- coding: utf-8 -*-
from __future__ import annotations
import os, traceback, tkinter as tk
from tkinter import messagebox, ttk
CREDIT = "Cr\u00e9ation et D\u00e9veloppement par JF GUILARD"

class MenuDemarrage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MEDICONF")
        self.geometry("760x460")
        self.minsize(640, 380)
        self.configure(bg="#eef2f6")
        ttk.Label(self, text="MEDICONF", font=("Segoe UI", 22, "bold"), background="#eef2f6", foreground="#1f4e79").pack(pady=(28, 4))
        ttk.Label(self, text=CREDIT, background="#eef2f6").pack(pady=(0, 2))
        ttk.Label(self, text="Choisissez le module a lancer", background="#eef2f6").pack(pady=(0, 22))
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
        try:
            self.quit(); self.destroy()
        except tk.TclError:
            pass
        os._exit(0)
    def _ouvrir_pdf(self):
        try:
            from patches_ui import appliquer, brancher
            from app import ConvertisseurApp
            appliquer(ConvertisseurApp)
            self.withdraw()
            try:
                fen = ConvertisseurApp(self)
            except TypeError:
                fen = ConvertisseurApp()
            try:
                brancher(fen, self)
            except Exception:
                messagebox.showerror("MEDICONF", traceback.format_exc()[-1200:])
            fen.lift()
        except Exception:
            self.deiconify()
            messagebox.showerror("MEDICONF", traceback.format_exc()[-1200:])
    def _ouvrir_texte(self):
        try:
            from reception import ReceptionApp
            self.withdraw()
            ReceptionApp(self)
        except Exception:
            self.deiconify()
            messagebox.showerror("MEDICONF", traceback.format_exc()[-1200:])
