"""Fios de luz: linhas de fluxo com espaçamento uniforme (Jobard & Lefer, 1997).

Um campo de direções suave (ondas de seno, quase horizontal) diz para onde o
"vento" corre. Os fios são semeados lado a lado, a `dsep` uns dos outros, e
param quando chegam perto demais de outro fio ou saem da região (a máscara
das letras do nome, ou um retângulo do painel).

Daqui saem: os contornos das letras (paths SVG), a máscara delas (para saber
o que é "dentro"), os fios e o texto de cada path, já enxuto.
"""
from __future__ import annotations

import io
import math
import random
from collections import defaultdict, deque
from typing import Callable, Iterable

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from PIL import Image, ImageDraw, ImageFont

from identidade import abrir_fonte, fonte_estatica, medir
from luz import Fio, Ponto, caminho, comprimento  # noqa: F401 (reexportados)

# ---------------------------------------------------------------- campo
class Campo:
    """Direção do vento em cada ponto: quase horizontal, com ondas largas que se cruzam."""

    def __init__(self, base: float = -0.05, ondas: Iterable[tuple[float, float, float, float]] | None = None):
        self.base = base
        # (amplitude em rad, frequência em x, frequência em y, fase)
        self.ondas = list(ondas or [(0.36, 0.0095, 0.0055, 0.7), (0.20, 0.0180, -0.0120, 2.3),
                                    (0.08, 0.0400, 0.0300, 4.1)])

    def direcao(self, x: float, y: float) -> Ponto:
        a = self.base + sum(amp * math.sin(kx * x + ky * y + f) for amp, kx, ky, f in self.ondas)
        return math.cos(a), math.sin(a)


# ---------------------------------------------------------------- letras
Linha = tuple[str, float, float, float, int, float]  # texto, x, y da base, tamanho, peso, espaço (em)


def _posicoes(texto: str, x: float, tamanho: float, peso: int, espaco_em: float) -> list[tuple[str, float]]:
    """Onde cada letra começa, pela mesma conta de avanço que o navegador faz (sem kerning)."""
    saida = []
    for c in texto:
        saida.append((c, x))
        x += medir(c, tamanho, peso, espaco_em)
    return saida


def contornos(linhas: Iterable[Linha]) -> str:
    """As letras como <path> (um por glifo), na posição exata do texto."""
    partes = []
    for texto, x, y, tamanho, peso, espaco_em in linhas:
        fonte = abrir_fonte(peso)
        glifos = fonte.getGlyphSet()
        cmap = fonte.getBestCmap()
        k = tamanho / fonte["head"].unitsPerEm
        for c, xc in _posicoes(texto, x, tamanho, peso, espaco_em):
            if c == " ":
                continue
            caneta = SVGPathPen(glifos)
            glifos[cmap[ord(c)]].draw(caneta)
            partes.append(f'<path transform="translate({xc:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})" '
                          f'd="{caneta.getCommands()}"/>')
    return "".join(partes)


def mascara(linhas: Iterable[Linha], largura: float, altura: float, escala: int = 4) -> np.ndarray:
    """Imagem booleana das letras (escala px por unidade do viewBox)."""
    img = Image.new("L", (math.ceil(largura * escala), math.ceil(altura * escala)), 0)
    lapis = ImageDraw.Draw(img)
    for texto, x, y, tamanho, peso, espaco_em in linhas:
        fonte = ImageFont.truetype(io.BytesIO(fonte_estatica(peso)), round(tamanho * escala),
                                   layout_engine=ImageFont.Layout.BASIC)
        for c, xc in _posicoes(texto, x, tamanho, peso, espaco_em):
            lapis.text((xc * escala, y * escala), c, font=fonte, fill=255, anchor="ls")
    return np.asarray(img) > 127


def dentro_da_mascara(m: np.ndarray, escala: int = 4) -> Callable[[float, float], bool]:
    alt, larg = m.shape

    def dentro(x: float, y: float) -> bool:
        i, j = int(y * escala), int(x * escala)
        return 0 <= i < alt and 0 <= j < larg and bool(m[i, j])
    return dentro


# ---------------------------------------------------------------- fios
def tecer(campo: Campo, dentro: Callable[[float, float], bool], caixa: tuple[float, float, float, float],
          dsep: float, *, passo: float = 0.8, teste: float = 0.5, borda_exata: bool = False,
          comprimento_min: float = 2.0, max_passos: int = 5000, semente: int = 1) -> list[Fio]:
    """Fios uniformemente espaçados dentro da região.

    dsep: distância entre fios vizinhos. teste: fração de dsep em que um fio para
    ao encostar noutro. borda_exata: o fio termina exatamente na borda da região
    (bissecção), para as letras terem contorno limpo."""
    x0, y0, x1, y1 = caixa
    grade: dict[tuple[int, int], list[Ponto]] = defaultdict(list)
    dtest = dsep * teste
    rnd = random.Random(semente)

    def chave(x: float, y: float) -> tuple[int, int]:
        return int((x - x0) // dsep), int((y - y0) // dsep)

    def perto(x: float, y: float, d: float) -> bool:
        i, j = chave(x, y)
        d2 = d * d
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for px, py in grade.get((i + di, j + dj), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < d2:
                        return True
        return False

    def seguir(x: float, y: float, sentido: int) -> Fio:
        pts: Fio = []
        h = passo * sentido
        for _ in range(max_passos):
            dx, dy = campo.direcao(x, y)
            dx, dy = campo.direcao(x + dx * h * 0.5, y + dy * h * 0.5)   # ponto médio (RK2)
            nx, ny = x + dx * h, y + dy * h
            if not dentro(nx, ny):
                if borda_exata:
                    a, b = 0.0, 1.0
                    for _ in range(7):
                        m = (a + b) / 2
                        if dentro(x + (nx - x) * m, y + (ny - y) * m):
                            a = m
                        else:
                            b = m
                    if a > 0:
                        pts.append((x + (nx - x) * a, y + (ny - y) * a))
                break
            if perto(nx, ny, dtest):
                break
            pts.append((nx, ny))
            x, y = nx, ny
        return pts

    fios: list[Fio] = []
    fila: deque[Ponto] = deque()

    def tentar(sx: float, sy: float) -> None:
        if not dentro(sx, sy) or perto(sx, sy, dsep * 0.96):
            return
        linha = seguir(sx, sy, -1)[::-1] + [(sx, sy)] + seguir(sx, sy, 1)
        if comprimento(linha) < comprimento_min:
            return
        fios.append(linha)
        for p in linha:
            grade[chave(*p)].append(p)
        # sementes novas dos dois lados, a cada ~dsep ao longo do fio
        a_cada = max(1, round(dsep / passo))
        for k in range(0, len(linha), a_cada):
            x, y = linha[k]
            dx, dy = campo.direcao(x, y)
            for s in (1, -1):
                fila.append((x - dy * dsep * s, y + dx * dsep * s))

    # sementes iniciais numa grade com tremor, da esquerda para a direita (cobre letras separadas)
    iniciais = []
    passo_semente = dsep * 3
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            iniciais.append((x + rnd.uniform(0, passo_semente), y + rnd.uniform(0, passo_semente)))
            x += passo_semente
        y += passo_semente
    iniciais.sort()
    for s in iniciais:
        tentar(*s)
        while fila:
            tentar(*fila.popleft())
    return fios


def enxugar(fio: Fio, tolerancia: float = 0.12) -> Fio:
    """Ramer–Douglas–Peucker: tira os pontos que não mudam a forma (o fio é suave)."""
    if len(fio) < 3:
        return fio
    p = np.asarray(fio)
    manter = np.zeros(len(p), dtype=bool)
    manter[0] = manter[-1] = True
    pilha = [(0, len(p) - 1)]
    while pilha:
        a, b = pilha.pop()
        if b <= a + 1:
            continue
        seg = p[b] - p[a]
        n = math.hypot(*seg) or 1.0
        meio = p[a + 1:b] - p[a]
        dist = np.abs(meio[:, 0] * seg[1] - meio[:, 1] * seg[0]) / n
        i = int(np.argmax(dist))
        if dist[i] > tolerancia:
            k = a + 1 + i
            manter[k] = True
            pilha += [(a, k), (k, b)]
    return [tuple(q) for q in p[manter]]
