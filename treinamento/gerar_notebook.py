"""Converte treino.py (células marcadas com '# %%') em treino.ipynb."""
import json
import re
from pathlib import Path

aqui = Path(__file__).resolve().parent
texto = (aqui / "treino.py").read_text(encoding="utf-8")
blocos = re.split(r"^# %%(.*)$", texto, flags=re.M)
cells = []
for marcador, corpo in zip(blocos[1::2], blocos[2::2]):
    corpo = corpo.strip("\n")
    if "[markdown]" in marcador:
        linhas = [l[2:] if l.startswith("# ") else l.lstrip("#") for l in corpo.splitlines()]
        cells.append({"cell_type": "markdown", "metadata": {}, "source": "\n".join(linhas)})
    else:
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                      "outputs": [], "source": corpo})
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
(aqui / "treino.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("treino.ipynb gerado com", len(cells), "células")
