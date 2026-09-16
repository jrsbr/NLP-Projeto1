"""Gera os SVG que dependem dos CSVs: o grafo de um caso e as barras de resultado.

O `build_pdf.py` chama estas funcoes para substituir os marcadores `__SVG_CASO__` e
`__BARRAS__` do apresentacao.md. A razao de gerar em vez de desenhar a mao: figura e
numero do slide ficam amarrados a data/processed/, e nao a uma captura de tela que
envelhece silenciosamente quando o pipeline roda de novo.

Por que gerar em vez de tirar print do visualizador: o SVG entra vetorial no PDF
(nao pixeliza na projecao) e os numeros do slide ficam amarrados aos CSVs, nao a
uma captura de tela que envelhece.

Duas decisoes de leitura, ambas para tirar poluicao do desenho:

1. As arestas que saem do Patient nao levam rotulo. Elas sao previsiveis pelo tipo
   do no de destino (Symptom sempre PRESENTS_WITH, Exam sempre UNDERWENT_EXAM, e
   assim por diante), entao o rotulo repetido quinze vezes em volta do centro so
   atrapalha. A legenda do slide cobre essa camada.
2. Rotulo aparece so nas arestas entre entidades, que sao as inferidas por regra
   e as unicas que o publico precisa ler uma por uma.

Uso direto, para inspecionar uma figura isolada:
    python3 assets/slides/figuras.py caso PMC7102447_01
    python3 assets/slides/figuras.py barras
"""

from __future__ import annotations

import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# (preenchimento, traco) por tipo de no, na paleta do deck
CORES = {
    "Patient": ("#12212e", "#12212e"),
    "History": ("#e6e9fb", "#4338ca"),
    "Symptom": ("#fdeceb", "#c0392b"),
    "Diagnosis": ("#e7f5ee", "#1c8a60"),
    "Exam": ("#eaf2f8", "#2b7fb0"),
    "ExamResult": ("#e3f6fa", "#0e7490"),
    "Finding": ("#fbe9f1", "#be185d"),
    "Treatment": ("#faf1e2", "#b07d24"),
    "AnatomicalSite": ("#f3effa", "#6c4ca8"),
    "Unit": ("#eef3f7", "#5b7183"),
}

# aresta automatica com o Patient: nao recebe rotulo no desenho
ESPINHA = {
    "PRESENTS_WITH",
    "DIAGNOSED_WITH",
    "UNDERWENT_EXAM",
    "UNDERWENT_TREATMENT",
    "HAS_HISTORY",
}

L, A = 1120, 460          # viewBox, na proporcao da caixa do slide
CX, CY = L / 2, 222
R1, R2 = 178, 262         # raios dos dois aneis
LARGURA_ROTULO = 14       # caracteres por linha antes de quebrar
DIST_MIN_ROTULO = 40      # px: abaixo disso dois rotulos de aresta se sobrepoem


def quebrar(texto: str, largura: int = LARGURA_ROTULO, maximo: int = 2) -> list[str]:
    """Quebra o rotulo em no maximo `maximo` linhas, com reticencia se sobrar texto."""
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        candidata = f"{atual} {p}".strip()
        if len(candidata) <= largura:
            atual = candidata
        else:
            if atual:
                linhas.append(atual)
            atual = p
            if len(linhas) == maximo:
                break
    if atual and len(linhas) < maximo:
        linhas.append(atual)
    if not linhas:
        return [texto[:largura]]
    consumido = len(" ".join(linhas).split())
    if consumido < len(palavras):
        linhas[-1] = linhas[-1][: largura - 1] + "…"
    return linhas


def carregar(caso: str):
    nos = {
        n["node_id"]: n
        for n in csv.DictReader(open(RAIZ / "data" / "processed" / "nodes.csv"))
    }
    arestas = [
        e
        for e in csv.DictReader(open(RAIZ / "data" / "processed" / "edges.csv"))
        if e["case_id"] == caso
    ]
    usados = {e["source_id"] for e in arestas} | {e["target_id"] for e in arestas}
    usados |= {i for i, n in nos.items() if n["case_id"] == caso}
    return {i: nos[i] for i in usados if i in nos}, arestas


def posicionar(nos: dict, arestas: list, centro: str) -> dict[str, tuple[float, float]]:
    """Dois aneis por distancia ao Patient, cada anel ordenado por tipo.

    Agrupar por tipo antes de distribuir o angulo mantem no mesmo setor do circulo
    os nos que o publico vai comparar entre si.
    """
    vizinhos = defaultdict(set)
    for e in arestas:
        vizinhos[e["source_id"]].add(e["target_id"])
        vizinhos[e["target_id"]].add(e["source_id"])

    anel1 = sorted(vizinhos[centro], key=lambda i: (nos[i]["type"], nos[i]["label"]))
    resto = [i for i in nos if i != centro and i not in vizinhos[centro]]
    anel2 = sorted(resto, key=lambda i: (nos[i]["type"], nos[i]["label"]))

    pos = {centro: (CX, CY)}
    for anel, raio, deslocamento in ((anel1, R1, -90), (anel2, R2, -90 + 12)):
        if not anel:
            continue
        for k, ident in enumerate(anel):
            ang = math.radians(deslocamento + 360 * k / len(anel))
            # o anel e achatado em 0.62 porque a pagina e 16:9, nao quadrada
            pos[ident] = (CX + raio * 1.52 * math.cos(ang), CY + raio * 0.62 * math.sin(ang))
    return pos


def _legenda(tipos: list[str]) -> list[str]:
    """Faixa de cor por tipo de no, no pe do desenho.

    Substitui o rotulo em cada aresta: num grafo de 20 nos o texto da relacao sempre
    caia em cima do nome de algum no. O vocabulario de relacoes esta na tabela do
    slide anterior, entao aqui o que falta identificar e a cor.
    """
    passo = L / len(tipos)
    y = A - 10
    saida = []
    for k, tipo in enumerate(tipos):
        x = passo * k + 16
        preenche, traco = CORES.get(tipo, ("#eef3f7", "#5b7183"))
        saida.append(
            f'<circle cx="{x:.1f}" cy="{y - 4:.1f}" r="6" fill="{preenche}"'
            f' stroke="{traco}" stroke-width="1.8"/>'
        )
        saida.append(
            f'<text x="{x + 12:.1f}" y="{y:.1f}" font-size="11.5" fill="#3b5364">{tipo}</text>'
        )
    return saida


def desenhar(caso: str) -> str:
    nos, arestas = carregar(caso)
    centro = next(i for i, n in nos.items() if n["type"] == "Patient")
    pos = posicionar(nos, arestas, centro)

    partes = [f'<svg class="dg" viewBox="0 0 {L} {A}" role="img">']

    # arestas primeiro, para passarem por tras dos nos
    for e in arestas:
        o, d = pos.get(e["source_id"]), pos.get(e["target_id"])
        if not o or not d:
            continue
        espinha = e["relation"] in ESPINHA
        classe = "ln fina" if espinha else "ln"
        partes.append(
            f'<line class="{classe}" x1="{o[0]:.1f}" y1="{o[1]:.1f}"'
            f' x2="{d[0]:.1f}" y2="{d[1]:.1f}" marker-end="url(#seta)"/>'
        )

    for ident, no in nos.items():
        x, y = pos[ident]
        preenche, traco = CORES.get(no["type"], ("#eef3f7", "#5b7183"))
        raio = 21 if ident == centro else 13
        partes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{raio}"'
            f' fill="{preenche}" stroke="{traco}" stroke-width="2"/>'
        )
        rotulo = "paciente" if ident == centro else no["label"]
        linhas = quebrar(rotulo)
        base = y + raio + 13
        cor = "#12212e" if ident == centro else traco
        peso = "700" if ident == centro else "600"
        for k, linha in enumerate(linhas):
            partes.append(
                f'<text x="{x:.1f}" y="{base + k * 12:.1f}" text-anchor="middle"'
                f' font-size="11" font-weight="{peso}" fill="{cor}"'
                # contorno branco atras do texto: o rotulo continua legivel quando
                # cai em cima de uma aresta
                f' style="paint-order:stroke;stroke:#fff;stroke-width:3.4px;'
                f'stroke-linejoin:round">'
                f'{linha.replace("&", "&amp;").replace("<", "&lt;")}</text>'
            )

    partes += _legenda(sorted({n["type"] for n in nos.values()}))
    partes.append("</svg>")
    return "\n".join(partes)


BL, BA = 1120, 336                    # viewBox das barras
BARRA_H, LINHA_H, LARGURA_MAX = 15, 29, 250

# cor da barra: o tipo do no, ou o tipo dominante na relacao
COR_RELACAO = {
    "UNDERWENT_EXAM": "Exam",
    "PERFORMED_ON": "Exam",
    "UNDERWENT_TREATMENT": "Treatment",
    "TARGETS": "Treatment",
    "TREATED_BY": "Treatment",
    "PRESENTS_WITH": "Symptom",
    "LOCATED_IN": "AnatomicalSite",
    "DIAGNOSED_WITH": "Diagnosis",
    "SUPPORTS": "Diagnosis",
    "REVEALS": "Finding",
    "HAS_RESULT": "ExamResult",
    "HAS_UNIT": "Unit",
    "HAS_HISTORY": "History",
    "CONFIRMS": "Diagnosis",
    "EXCLUDES": "Symptom",
}


def _coluna(itens: list[tuple[str, int]], x_rotulo: float, x_barra: float, cores: list[str]) -> list[str]:
    """Uma coluna de barras horizontais. `itens` ja vem ordenado do maior para o menor."""
    maximo = max(v for _, v in itens)
    partes = []
    for k, ((nome, valor), cor) in enumerate(zip(itens, cores)):
        y = 36 + k * LINHA_H
        largura = LARGURA_MAX * valor / maximo
        partes.append(
            f'<text x="{x_rotulo}" y="{y + 12}" text-anchor="end" font-size="11.5"'
            f' fill="#3b5364">{nome}</text>'
        )
        partes.append(
            f'<rect x="{x_barra}" y="{y}" width="{largura:.1f}" height="{BARRA_H}"'
            f' rx="2.5" fill="{cor}"/>'
        )
        partes.append(
            f'<text x="{x_barra + largura + 8:.1f}" y="{y + 12}" font-size="11.5"'
            f' font-weight="700" fill="#12212e">{valor}</text>'
        )
    return partes


def barras() -> str:
    """Barras de nos por tipo e das 10 relacoes mais frequentes."""
    nos = list(csv.DictReader(open(RAIZ / "data" / "processed" / "nodes.csv")))
    arestas = list(csv.DictReader(open(RAIZ / "data" / "processed" / "edges.csv")))

    por_tipo = Counter(n["type"] for n in nos).most_common()
    por_relacao = Counter(e["relation"] for e in arestas).most_common(10)

    partes = _coluna(
        por_tipo, 150, 158, [CORES.get(t, ("", "#5b7183"))[1] for t, _ in por_tipo]
    )
    partes += _coluna(
        por_relacao,
        766,
        774,
        [CORES.get(COR_RELACAO.get(r, ""), ("", "#5b7183"))[1] for r, _ in por_relacao],
    )
    return "\n".join(partes)


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "caso"
    if alvo == "barras":
        print(barras())
    else:
        print(desenhar(sys.argv[2] if len(sys.argv) > 2 else "PMC7102447_01"))
