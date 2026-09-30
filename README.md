# MEDICONF

Conversion de documents en masse pour les insertions dans les dossiers patients HelloDoc.

Application Windows : images (JPG, PNG, BMP, GIF, TIFF, WEBP…) et documents (TXT, RTF, DOC, DOCX, ODT) vers PDF.

## Lancer le code

```bat
lancer.bat
```

ou :

```bat
pip install -r requirements.txt
python app.py
```

## Compiler l.exe Windows

Onglet **Actions** du depot → workflow **Compiler Windows** → télécharger l'artefact **MEDICONF-Windows** (`MEDICONF.exe`).

Le build part automatiquement à chaque push sur `main`, ou manuellement via **Run workflow**.

DOC / RTF / ODT : installer [LibreOffice](https://www.libreoffice.org/download/) sur le PC qui convertit.
