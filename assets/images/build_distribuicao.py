"""Regera `distribuicao-grafo.png`, a figura de contagens da secao Resultados.

Existe porque a figura tem numeros dentro dela: sem um gerador versionado, ela
silenciosamente descasa do `nodes.csv`/`edges.csv` na primeira vez que o pipeline
muda. Reaproveita a paleta e o desenho de barras do deck (`assets/slides/figuras.py`)
para o README e os slides nao divergirem visualmente.

Diferenca em relacao a figura do slide: aqui entram todas as relacoes, nao so as
10 mais frequentes, porque no README ha espaco e a cauda importa (`CONFIRMS` e
`EXCLUDES` sao discutidos no texto).

    python3 assets/images/build_distribuicao.py

Precisa do Chrome instalado, igual ao `build_pdf.py`, que faz a rasterizacao.
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "assets" / "slides"))

from figuras import CORES, COR_RELACAO, LINHA_H, _coluna  # noqa: E402

SAIDA = RAIZ / "assets" / "images" / "distribuicao-grafo.png"
ESCALA = 2  # rasteriza em 2x: o README e lido com zoom


def _titulo(x: float, texto: str) -> str:
    return (
        f'<text x="{x}" y="20" font-size="14" font-weight="700"'
        f' fill="#3b5364">{texto}</text>'
    )


def montar_svg() -> tuple[str, int, int]:
    nos = list(csv.DictReader(open(RAIZ / "data" / "processed" / "nodes.csv")))
    arestas = list(csv.DictReader(open(RAIZ / "data" / "processed" / "edges.csv")))

    por_tipo = Counter(n["type"] for n in nos).most_common()
    por_relacao = Counter(e["relation"] for e in arestas).most_common()

    largura = 1120
    altura = 36 + max(len(por_tipo), len(por_relacao)) * LINHA_H + 8

    partes = [
        _titulo(28, f"Nós por tipo ({len(nos)})"),
        _titulo(644, f"Arestas por relação ({len(arestas)})"),
    ]
    partes += _coluna(
        por_tipo, 150, 158, [CORES.get(t, ("", "#5b7183"))[1] for t, _ in por_tipo]
    )
    partes += _coluna(
        por_relacao,
        766,
        774,
        [CORES.get(COR_RELACAO.get(r, ""), ("", "#5b7183"))[1] for r, _ in por_relacao],
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}"'
        f' width="{largura * ESCALA}" height="{altura * ESCALA}"'
        f' font-family="-apple-system, Helvetica, Arial, sans-serif">'
        f'<rect width="{largura}" height="{altura}" fill="#fff"/>'
        + "\n".join(partes)
        + "</svg>"
    )
    return svg, largura * ESCALA, altura * ESCALA


def achar_chrome() -> str:
    candidatos = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    )
    for c in candidatos:
        if Path(c).exists():
            return c
    from shutil import which

    for nome in ("google-chrome", "chromium", "chromium-browser"):
        if caminho := which(nome):
            return caminho
    sys.exit("Chrome nao encontrado (mesma dependencia do assets/slides/build_pdf.py).")


def main() -> None:
    svg, largura, altura = montar_svg()
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "barras.html"
        html.write_text(
            f'<!doctype html><meta charset="utf-8">'
            f"<style>html,body{{margin:0;padding:0;background:#fff}}</style>{svg}",
            encoding="utf-8",
        )
        subprocess.run(
            [
                achar_chrome(),
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--default-background-color=ffffff",
                f"--screenshot={SAIDA}",
                f"--window-size={largura},{altura}",
                html.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    print(f"{SAIDA.relative_to(RAIZ)} regerado ({largura}x{altura})")


if __name__ == "__main__":
    main()
