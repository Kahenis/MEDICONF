# -*- coding: utf-8 -*-
"""Couleurs de l'interface. Ne remplace aucun bouton ni aucune case."""

THEMES = {
    "basic": {
        "fond": "#f4f6f8",
        "accent": "#1f4e79",
        "texte": "#1a1a1a",
        "bouton": "#e8eaed",
        "bouton_texte": "#1a1a1a",
        "zone": "#ffffff",
    },
    "medical": {
        "fond": "#f7f1f1",
        "accent": "#b42318",
        "texte": "#1d3557",
        "bouton": "#1d4e89",
        "bouton_texte": "#ffffff",
        "zone": "#ffffff",
    },
    "pro": {
        "fond": "#eef5f8",
        "accent": "#0b6e8a",
        "texte": "#16324f",
        "bouton": "#0b6e8a",
        "bouton_texte": "#ffffff",
        "zone": "#ffffff",
    },
}


def appliquer(fen, nom: str) -> None:
    import tkinter as tk
    from tkinter import ttk
    couleurs = THEMES.get(nom, THEMES["basic"])
    try:
        fen.configure(bg=couleurs["fond"])
    except Exception:
        pass
    style = ttk.Style(fen)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TFrame", background=couleurs["fond"])
    style.configure("TLabel", background=couleurs["fond"], foreground=couleurs["texte"])
    style.configure("Titre.TLabel", background=couleurs["fond"], foreground=couleurs["accent"])
    style.configure("Info.TLabel", background=couleurs["fond"], foreground=couleurs["texte"])
    style.configure("TLabelframe", background=couleurs["fond"])
    style.configure("TLabelframe.Label", background=couleurs["fond"], foreground=couleurs["accent"])
    style.configure("TButton", background=couleurs["bouton"], foreground=couleurs["bouton_texte"], padding=6)
    style.configure("TNotebook", background=couleurs["fond"])
    style.configure("TNotebook.Tab", padding=(14, 6))
    style.map("TButton", background=[("active", couleurs["accent"])], foreground=[("active", "#ffffff")])
