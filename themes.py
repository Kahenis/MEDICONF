# -*- coding: utf-8 -*-
"""Thème fixe : blanc, bleu, vert, rouge. Ne remplace aucun bouton ni aucune case."""


def appliquer(fen) -> None:
    from tkinter import ttk
    fond, bleu, vert, rouge = "#ffffff", "#1d4e89", "#15803d", "#b42318"
    try:
        fen.configure(bg=fond)
    except Exception:
        pass
    style = ttk.Style(fen)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TFrame", background=fond)
    style.configure("TLabel", background=fond, foreground=bleu)
    style.configure("Titre.TLabel", background=fond, foreground=bleu, font=("Segoe UI", 16, "bold"))
    style.configure("Info.TLabel", background=fond, foreground="#333")
    style.configure("TLabelframe", background=fond, bordercolor=bleu)
    style.configure("TLabelframe.Label", background=fond, foreground=rouge, font=("Segoe UI", 10, "bold"))
    style.configure("TButton", background=vert, foreground="#ffffff", padding=6)
    style.map("TButton", background=[("active", bleu)], foreground=[("active", "#ffffff")])
    style.configure("TNotebook", background=fond)
    style.configure("TNotebook.Tab", padding=(10, 4), font=("Segoe UI", 9), background="#e8eef5", foreground=bleu)
    style.map(
        "TNotebook.Tab",
        background=[("selected", bleu), ("!selected", "#e8eef5")],
        foreground=[("selected", "#ffffff"), ("!selected", bleu)],
        padding=[("selected", (22, 12)), ("!selected", (8, 3))],
        font=[("selected", ("Segoe UI", 13, "bold")), ("!selected", ("Segoe UI", 9))],
        expand=[("selected", [6, 6, 6, 0])],
    )

