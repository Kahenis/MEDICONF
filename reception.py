# -*- coding: utf-8 -*-
from __future__ import annotations
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from ocr import extraire_avec_ocr, texte_utile

COULEUR_FOND = "#f4f6f8"
COULEUR_ACCENT = "#0d7377"
APP_TITRE = "MEDICONF - PDF vers texte HelloDoc"

def extraire_texte_pdf(chemin: Path) -> str:
    from pypdf import PdfReader
    lecteur = PdfReader(str(chemin))
    pages = []
    for i, page in enumerate(lecteur.pages, 1):
        brut = page.extract_text() or ""
        pages.append(f"--- Page {i} ---\n{brut.strip()}")
    return "\n\n".join(pages).strip()

def nettoyer_texte(texte: str) -> str:
    lignes = [" ".join(l.split()) for l in texte.splitlines()]
    out, vide = [], 0
    for l in lignes:
        if not l:
            vide += 1
            if vide <= 1:
                out.append("")
        else:
            vide = 0
            out.append(l)
    return "\n".join(out).strip()

class ReceptionApp(tk.Toplevel):
    def __init__(self, master=None) -> None:
        if master is None:
            root = tk.Tk(); root.withdraw(); super().__init__(root); self._owns_root = True
        else:
            super().__init__(master); self._owns_root = False; master.withdraw()
        self.title(APP_TITRE)
        self.geometry("980x680")
        self.configure(bg=COULEUR_FOND)
        self.pdf_path = None
        self._construire()
        self.protocol("WM_DELETE_WINDOW", self._quitter)

    def _construire(self) -> None:
        ttk.Label(self, text="Conversion intelligente PDF vers texte\npour la boite de reception HelloDoc", font=("Segoe UI", 14, "bold"), background=COULEUR_FOND, foreground=COULEUR_ACCENT, justify="center").pack(pady=(14, 8))
        haut = ttk.Frame(self); haut.pack(fill="x", padx=14, pady=6)
        ttk.Button(haut, text="Ouvrir un PDF...", command=self._ouvrir).pack(side="left")
        self.lbl_fic = ttk.Label(haut, text="Aucun fichier", background=COULEUR_FOND)
        self.lbl_fic.pack(side="left", padx=10)
        ttk.Button(haut, text="Retour au menu", command=self._quitter).pack(side="right")
        actions = ttk.Frame(self); actions.pack(fill="x", padx=14, pady=4)
        ttk.Button(actions, text="Extraire le texte", command=self._extraire).pack(side="left")
        ttk.Button(actions, text="Copier tout", command=self._copier).pack(side="left", padx=6)
        ttk.Button(actions, text="Enregistrer en .txt...", command=self._sauver).pack(side="left")
        self.txt = tk.Text(self, wrap="word", font=("Segoe UI", 10), bg="#ffffff")
        sb = ttk.Scrollbar(self, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(6, 14))
        sb.pack(side="right", fill="y", pady=(6, 14), padx=(0, 14))
        self.txt.insert("1.0", "Ouvrez un PDF. Texte extractible direct, sinon reconnaissance de caracteres (OCR) automatique.")

    def _ouvrir(self) -> None:
        f = filedialog.askopenfilename(title="PDF source", filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")], parent=self)
        if not f:
            return
        self.pdf_path = Path(f)
        self.lbl_fic.configure(text=self.pdf_path.name)
        self._extraire()

    def _extraire(self) -> None:
        if not self.pdf_path:
            messagebox.showwarning(APP_TITRE, "Ouvrez d'abord un PDF.", parent=self)
            return
        try:
            propre = nettoyer_texte(extraire_texte_pdf(self.pdf_path))
            mode = "texte"
            if texte_utile(propre) < 40:
                brut, mode = extraire_avec_ocr(self.pdf_path, propre)
                propre = nettoyer_texte(brut)
        except Exception as e:
            messagebox.showerror(APP_TITRE, str(e), parent=self)
            return
        self.txt.delete("1.0", "end")
        entete = "Reconnaissance de caracteres (PDF scanne).\n\n" if mode == "ocr" else ""
        self.txt.insert("1.0", entete + (propre or "(Aucun texte reconnu.)"))

    def _copier(self) -> None:
        contenu = self.txt.get("1.0", "end").strip()
        if contenu:
            self.clipboard_clear(); self.clipboard_append(contenu)
            messagebox.showinfo(APP_TITRE, "Texte copie.", parent=self)

    def _sauver(self) -> None:
        contenu = self.txt.get("1.0", "end").strip()
        if not contenu:
            return
        initial = (self.pdf_path.stem + ".txt") if self.pdf_path else "hellodoc.txt"
        dest = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=initial, filetypes=[("Texte", "*.txt")], parent=self)
        if dest:
            Path(dest).write_text(contenu, encoding="utf-8")

    def _quitter(self) -> None:
        if self._owns_root:
            self.master.destroy()
        else:
            self.destroy()
            try:
                self.master.deiconify()
            except tk.TclError:
                pass
