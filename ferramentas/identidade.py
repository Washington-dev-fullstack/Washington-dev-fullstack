"""Identidade visual "Fios de luz", própria do perfil do GitHub.

Tudo o que os SVGs do README compartilham mora aqui: as cores, a fonte Syne
embutida (só com as letras usadas), a medição de texto e o CSS-base com a
regra de "reduzir movimento".

O sistema:
  fio   = a forma de tudo: o nome é tecido por fios; molduras e divisórias também
  âmbar = luz: só o que se move ou está ao vivo (pulsos, "disponível", hoje no gráfico)
  noite = o fundo de todo painel, um quase preto azulado (o portfólio é preto neutro)
"""
from __future__ import annotations

import base64
import io
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

PASTA = Path(__file__).resolve().parent
FONTES = PASTA / "fontes"
ASSETS = PASTA.parent / "assets"

# ---------------------------------------------------------------- cores
NOITE = "#0b0c10"
NOITE_2 = "#14161c"
TEXTO = "#f3eee6"
TEXTO_2 = "rgba(243,238,230,0.70)"
TEXTO_3 = "rgba(243,238,230,0.46)"
FIO = "rgba(243,238,230,0.10)"
FIO_FORTE = "rgba(243,238,230,0.22)"
AMBAR = "#ffb347"
AMBAR_CLARO = "#ffe3b3"
CORAL = "#ff7a45"

# Curvas
EASE_SAIDA = "cubic-bezier(0.22,1,0.36,1)"
SPLINE_SAIDA = "0.22 1 0.36 1"  # a mesma curva, no formato do SMIL
SPLINE_SUAVE = "0.45 0 0.25 1"

LARGURA = 880  # largura de todo painel (viewBox)
MARGEM = 48
CANTOS = 18    # raio dos cantos do painel

# ---------------------------------------------------------------- fontes
FAMILIA = "SY"
_ARQUIVO = "syne-wght.ttf"   # Syne variável (SIL Open Font License), eixo wght 400–800
PESOS = (400, 500, 600, 700, 800)


@lru_cache(maxsize=None)
def fonte_estatica(peso: int) -> bytes:
    """Syne estática (sem eixo variável) no peso pedido, como TTF em bytes."""
    if peso not in PESOS:
        raise ValueError(f"peso {peso} fora de {PESOS}")
    fonte = instancer.instantiateVariableFont(TTFont(FONTES / _ARQUIVO), {"wght": peso})
    fonte.flavor = None
    saida = io.BytesIO()
    fonte.save(saida)
    return saida.getvalue()


def abrir_fonte(peso: int) -> TTFont:
    return TTFont(io.BytesIO(fonte_estatica(peso)))


@lru_cache(maxsize=None)
def _avancos(peso: int) -> tuple[dict[int, int], int]:
    fonte = abrir_fonte(peso)
    cmap = fonte.getBestCmap()
    hmtx = fonte["hmtx"]
    return {cp: hmtx[nome][0] for cp, nome in cmap.items()}, fonte["head"].unitsPerEm


@lru_cache(maxsize=None)
def altura_maiuscula(peso: int = 800) -> float:
    """Altura das maiúsculas em em (para posicionar a linha de base)."""
    fonte = abrir_fonte(peso)
    return fonte["OS/2"].sCapHeight / fonte["head"].unitsPerEm


def faltando(texto: str, peso: int) -> set[str]:
    """Caracteres do texto que a fonte não tem (desenhe-os como forma)."""
    avancos, _ = _avancos(peso)
    return {c for c in texto if c not in "\n" and ord(c) not in avancos}


def medir(texto: str, tamanho: float, peso: int = 400, espaco_em: float = 0.0) -> float:
    """Largura do texto em unidades do viewBox (sem kerning, como os SVGs desenham:
    o CSS-base desliga o kerning para que esta conta bata com o navegador)."""
    avancos, upem = _avancos(peso)
    largura = sum(avancos.get(ord(c), upem // 2) for c in texto) / upem * tamanho
    return largura + len(texto) * espaco_em * tamanho


def quebrar(texto: str, largura_max: float, tamanho: float, peso: int = 400, espaco_em: float = 0.0) -> list[str]:
    """Quebra gulosa de linhas por palavra."""
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if atual and medir(teste, tamanho, peso, espaco_em) > largura_max:
            linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    if atual:
        linhas.append(atual)
    return linhas


def fonte_css(usos: dict[int, str]) -> str:
    """@font-face com cada peso reduzido às letras usadas, em woff2 base64.
    `usos` = {peso: texto que usa esse peso}."""
    blocos = []
    for peso, texto in sorted(usos.items()):
        if not texto:
            continue
        opcoes = Options()
        opcoes.flavor = "woff2"
        opcoes.layout_features = []  # sem kerning nem ligaduras: a medição é por avanço
        opcoes.name_IDs = []
        opcoes.notdef_outline = False
        sub = Subsetter(opcoes)
        fonte = abrir_fonte(peso)
        sub.populate(text=texto + " ")
        sub.subset(fonte)
        fonte.flavor = "woff2"
        saida = io.BytesIO()
        fonte.save(saida)
        dados = base64.b64encode(saida.getvalue()).decode()
        blocos.append(
            f"@font-face{{font-family:{FAMILIA};font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{dados}) format('woff2')}}"
        )
    return "".join(blocos)


# ---------------------------------------------------------------- texto
def esc(texto: str) -> str:
    return escape(texto, {'"': "&quot;"})


class Textos:
    """Junta o texto usado em cada peso enquanto o SVG é montado, para o
    subconjunto da fonte ter exatamente essas letras."""

    def __init__(self):
        self.usos: dict[int, str] = {}

    def usar(self, texto: str, peso: int) -> str:
        atual = self.usos.get(peso, "")
        novos = "".join(sorted(set(texto) - set(atual)))
        self.usos[peso] = atual + novos
        return texto

    def css(self) -> str:
        return fonte_css(self.usos)

    def texto(self, x, y, conteudo, *, tamanho, peso=400, cor=TEXTO, espaco_em=0.0,
              ancora="start", classe="", extra="") -> str:
        self.usar(conteudo, peso)
        ls = f' letter-spacing="{espaco_em * tamanho:.3f}"' if espaco_em else ""
        cls = f' class="{classe}"' if classe else ""
        return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FAMILIA}" font-weight="{peso}" '
                f'font-size="{tamanho}"{ls} fill="{cor}" text-anchor="{ancora}"{cls}{extra}>{esc(conteudo)}</text>')

    def paragrafo(self, texto: str, x: float, y: float, largura: float, tamanho: float, altura_linha: float, *,
                  cor: str = TEXTO_2, peso: int = 400, classe: str = "", extra: str = "") -> tuple[str, float]:
        """Texto quebrado em linhas. Devolve (svg, y da última linha)."""
        linhas = quebrar(texto, largura, tamanho, peso)
        partes = [self.texto(x, y + i * altura_linha, l, tamanho=tamanho, peso=peso, cor=cor, classe=classe, extra=extra)
                  for i, l in enumerate(linhas)]
        return "".join(partes), y + (len(linhas) - 1) * altura_linha


# ---------------------------------------------------------------- formas
def seta(x: float, y: float, tamanho: float = 12, cor: str = TEXTO, espessura: float = 1.7, classe: str = "") -> str:
    """↗ desenhada (a Syne não tem o glifo). (x, y) = canto inferior esquerdo."""
    t = tamanho
    cls = f' class="{classe}"' if classe else ""
    return (f'<path{cls} d="M{x:.2f} {y:.2f} L{x + t:.2f} {y - t:.2f} M{x + t * 0.3:.2f} {y - t:.2f} '
            f'L{x + t:.2f} {y - t:.2f} L{x + t:.2f} {y - t * 0.7:.2f}" fill="none" stroke="{cor}" '
            f'stroke-width="{espessura}" stroke-linecap="round" stroke-linejoin="round"/>')


def ponto_vivo(cx: float, cy: float, r: float = 3.5) -> str:
    """O ponto âmbar de "ao vivo": um anel sai dele e se apaga, devagar."""
    return (f'<circle class="anel" cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" fill="none" stroke="{AMBAR}" stroke-width="1.2"/>'
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" fill="{AMBAR}"/>')


# ---------------------------------------------------------------- CSS-base
CSS_BASE = """
text{font-kerning:none;text-rendering:geometricPrecision}
.anel{opacity:0;transform-box:fill-box;transform-origin:center;animation:anel 2.6s cubic-bezier(0.22,1,0.36,1) infinite}
@keyframes anel{0%{opacity:.8;transform:scale(1)}100%{opacity:0;transform:scale(3.4)}}
.estatico{display:none}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important}
  .animado{display:none}
  .estatico{display:inline}
}
"""


def svg(largura: float, altura: float, corpo: str, textos: Textos, css: str = "", titulo: str = "",
        fundo: str | None = NOITE, cantos: float = CANTOS) -> str:
    """Monta o documento SVG final com a fonte embutida. Com fundo, o painel tem cantos
    arredondados e tudo o que passa da borda (os fios) é recortado por eles."""
    rotulo = f"<title>{esc(titulo)}</title>" if titulo else ""
    aria = f' aria-label="{esc(titulo)}"' if titulo else ""
    if fundo:
        painel = (f'<clipPath id="painel"><rect width="{largura}" height="{altura}" rx="{cantos}"/></clipPath>'
                  f'<rect width="{largura}" height="{altura}" rx="{cantos}" fill="{fundo}"/>')
        corpo = f'{painel}<g clip-path="url(#painel)">{corpo}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}" role="img"{aria}>'
        f"{rotulo}<style>{textos.css()}{CSS_BASE}{css}</style>{corpo}</svg>"
    )


def salvar(nome: str, conteudo: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    caminho = ASSETS / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho
