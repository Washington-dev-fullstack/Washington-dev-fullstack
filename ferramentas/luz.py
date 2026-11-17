"""A luz que corre nos fios: pulsos (cometas), a divisória e o texto dos paths.

Fica à parte de fios.py porque não usa numpy nem Pillow: o gráfico de
contribuições, gerado pela Action todo dia, só precisa do fonttools.
"""
from __future__ import annotations

import math
import random
from typing import Iterable

from identidade import AMBAR, AMBAR_CLARO, EASE_SAIDA, FIO_FORTE, LARGURA as W, MARGEM as M

Ponto = tuple[float, float]
Fio = list[Ponto]

VELOCIDADE = 150  # px/s: a luz corre sempre na mesma velocidade, em qualquer fio


# ---------------------------------------------------------------- paths
def comprimento(fio: Fio) -> float:
    return sum(math.dist(a, b) for a, b in zip(fio, fio[1:]))


def _num(v: float) -> str:
    """Número curto: 1 casa, sem zero à esquerda (".5", "-.5")."""
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith("0.") or s.startswith("-0."):
        s = s.replace("0.", ".", 1)
    return "0" if s in ("-0", "") else s


def caminho(fios: Iterable[Fio]) -> str:
    """Vários fios num só atributo d, com coordenadas relativas (bem mais curto)."""
    partes = []
    for fio in fios:
        ax, ay = round(fio[0][0], 1), round(fio[0][1], 1)
        trecho = [f"M{_num(ax)} {_num(ay)}"]
        for x, y in fio[1:]:
            bx, by = round(x, 1), round(y, 1)
            dx, dy = bx - ax, by - ay
            if dx == 0 and dy == 0:
                continue
            dy_txt = _num(dy)
            trecho.append(f"l{_num(dx)}{'' if dy_txt.startswith('-') else ' '}{dy_txt}")
            ax, ay = bx, by
        partes.append("".join(trecho))
    return "".join(partes)


# ---------------------------------------------------------------- cometas
class Cometa:
    """Um pulso: o traço do fio (d), o pathLength normalizado e o estilo de tempo."""

    def __init__(self, d: str, comprimento_norm: float, estilo: str):
        self.d, self.pl, self.estilo = d, comprimento_norm, estilo


def cometas(linhas: list[Fio], rnd: random.Random, *, prefixo: str, periodo: float = 1500,
            cauda: float = 150, cabeca: float = 44) -> tuple[list[Cometa], str]:
    """Um pulso de luz por fio, todos na mesma velocidade e no mesmo período.

    Cada fio ganha pathLength = comprimento × (1000 / período): assim o período vale
    1000 em todos e um único @keyframes (0 → -1000) e as mesmas classes de traço
    servem para todos. A cauda e a cabeça terminam no mesmo ponto (o fim do traço
    é o fim do padrão), então a luz tem rastro.

    O estilo de cada cometa já traz um deslocamento fixo, que é o que fica no quadro
    parado do "reduzir movimento". Devolve (cometas, css)."""
    u = 1000 / periodo
    dur = periodo / VELOCIDADE
    saida = []
    for fio in linhas:
        L = comprimento(fio)
        assert L + cauda < periodo, "fio mais longo que o período do pulso"
        parado = -rnd.uniform(0.4, 0.8) * L * u      # quadro parado: a luz no meio do fio
        saida.append(Cometa(caminho([fio]), L * u,
                            f"stroke-dashoffset:{parado:.1f};animation-delay:{-rnd.uniform(0, dur):.2f}s"))
    css = ("@keyframes corre{from{stroke-dashoffset:0}to{stroke-dashoffset:-1000}}"
           f".c-{prefixo}{{animation:corre {dur:.2f}s linear infinite}}"
           f".ca-{prefixo}{{stroke-dasharray:0 {1000 - cauda * u:.1f} {cauda * u:.1f} 0}}"
           f".cb-{prefixo}{{stroke-dasharray:0 {1000 - cabeca * u:.1f} {cabeca * u:.1f} 0}}")
    return saida, css


def camadas_cometa(prefixo: str, lista: list[Cometa], camadas: list[tuple[str, str]]) -> str:
    """Cada camada de cada cometa é um <path> de verdade, com a animação nele mesmo.

    Medido no Chrome: <use> com o deslocamento herdado de um <g> custava ~10× mais
    por quadro (a árvore copiada do <use> é refeita a cada quadro). Repetir o d sai
    mais caro em bytes e muito mais barato em processador.
    camadas = [("cauda" | "cabeca", pintura)]."""
    cls = {"cauda": f"ca-{prefixo}", "cabeca": f"cb-{prefixo}"}
    return "".join(
        f'<path d="{c.d}" pathLength="{c.pl:.2f}" class="c-{prefixo} {cls[camada]}" style="{c.estilo}" {pintura}/>'
        for c in lista for camada, pintura in camadas)


# ---------------------------------------------------------------- fio que se desenha
CSS_DESENHA = (f".fio-desenha{{stroke-dasharray:1 2;animation:desenha 1.6s {EASE_SAIDA} both}}"
               "@keyframes desenha{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}")


def fio_divisor(y: float, rnd: random.Random, *, prefixo: str, x0: float = M, x1: float = W - M,
                atraso: float = 0.6) -> tuple[str, str]:
    """Divisória: um fio levemente ondulado, que se desenha na entrada e por onde a
    luz corre de vez em quando. Devolve (svg, css); some o CSS_DESENHA ao SVG."""
    pts = [(x, y + 2.2 * math.sin((x - x0) * 0.017 + 0.6)) for x in range(int(x0), int(x1) + 1, 6)]
    lista, css = cometas([pts], rnd, prefixo=prefixo, periodo=2600, cauda=160, cabeca=40)
    # o fio de base tem o próprio path: o pathLength="1" dele serve à entrada
    corpo = (f'<path d="{caminho([pts])}" pathLength="1" class="fio-desenha" fill="none" stroke="{FIO_FORTE}" '
             f'style="animation-delay:{atraso:.2f}s"/>'
             f'<g fill="none" stroke-linecap="round">' + camadas_cometa(prefixo, lista, [
                 ("cauda", f'stroke="{AMBAR}" stroke-opacity=".35" stroke-width="1.4"'),
                 ("cabeca", f'stroke="{AMBAR_CLARO}" stroke-width="1.8"')]) + "</g>")
    return corpo, css
