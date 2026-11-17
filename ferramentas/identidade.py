"""Identidade visual "Código → Render", portada do portfólio para SVG.

Tudo o que os SVGs do README compartilham mora aqui: as cores (tokens do
portfólio), as fontes embutidas (só com as letras usadas), a medição de texto
e o CSS-base com a regra de "reduzir movimento".

Regras do conceito (as mesmas do site):
  vazado = rascunho / futuro · sólido = entregue · verde = só o que está ao vivo
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
INK = "#050505"
INK_2 = "#0c0c0d"
PAPER = "#f2f2eb"
PAPER_INK = "#0b0b0b"
TEXT = "#f6f6f1"
TEXT_2 = "rgba(246,246,241,0.72)"
TEXT_3 = "rgba(246,246,241,0.52)"
LINE = "rgba(246,246,241,0.12)"
LINE_STRONG = "rgba(246,246,241,0.28)"
VAZADO = "rgba(246,246,241,0.55)"
SIGNAL = "#00ff66"

# Curvas do portfólio
EASE_RENDER = "cubic-bezier(0.16,1,0.3,1)"
EASE_WIPE = "cubic-bezier(0.65,0,0.35,1)"
SPLINE_RENDER = "0.16 1 0.3 1"  # a mesma curva, no formato do SMIL

LARGURA = 880  # largura de todo painel (viewBox)
MARGEM = 40

# ---------------------------------------------------------------- fontes
# família CSS → (arquivo, peso do eixo wght ou None se a fonte for estática)
_ARQUIVOS = {
    ("SG", 300): ("space-grotesk-latin-wght-normal.woff2", 300),
    ("SG", 400): ("space-grotesk-latin-wght-normal.woff2", 400),
    ("SG", 500): ("space-grotesk-latin-wght-normal.woff2", 500),
    ("SG", 700): ("space-grotesk-latin-wght-normal.woff2", 700),
    ("JB", 400): ("jetbrains-mono-latin-400-normal.woff2", None),
    ("JB", 500): ("jetbrains-mono-latin-500-normal.woff2", None),
}


@lru_cache(maxsize=None)
def _fonte_estatica(familia: str, peso: int) -> bytes:
    """Fonte estática (sem eixo variável) no peso pedido, como TTF em bytes."""
    arquivo, eixo = _ARQUIVOS[(familia, peso)]
    fonte = TTFont(FONTES / arquivo)
    if eixo is not None:
        fonte = instancer.instantiateVariableFont(fonte, {"wght": eixo})
    fonte.flavor = None
    saida = io.BytesIO()
    fonte.save(saida)
    return saida.getvalue()


def _abrir(familia: str, peso: int) -> TTFont:
    return TTFont(io.BytesIO(_fonte_estatica(familia, peso)))


@lru_cache(maxsize=None)
def _avancos(familia: str, peso: int) -> tuple[dict[int, int], int]:
    fonte = _abrir(familia, peso)
    cmap = fonte.getBestCmap()
    hmtx = fonte["hmtx"]
    return {cp: hmtx[nome][0] for cp, nome in cmap.items()}, fonte["head"].unitsPerEm


def altura_maiuscula(familia: str = "SG", peso: int = 700) -> float:
    """Altura das maiúsculas em em (para posicionar a linha de base)."""
    fonte = _abrir(familia, peso)
    return fonte["OS/2"].sCapHeight / fonte["head"].unitsPerEm


def faltando(texto: str, familia: str, peso: int) -> set[str]:
    """Caracteres do texto que a fonte não tem (desenhe-os como forma)."""
    avancos, _ = _avancos(familia, peso)
    return {c for c in texto if c not in "\n" and ord(c) not in avancos}


def medir(texto: str, tamanho: float, familia: str = "SG", peso: int = 700, espaco_em: float = 0.0) -> float:
    """Largura do texto em unidades do viewBox (sem kerning, como os SVGs desenham:
    o CSS-base desliga o kerning para que esta conta bata com o navegador)."""
    avancos, upem = _avancos(familia, peso)
    largura = sum(avancos.get(ord(c), upem // 2) for c in texto) / upem * tamanho
    return largura + len(texto) * espaco_em * tamanho


def quebrar(texto: str, largura_max: float, tamanho: float, familia="SG", peso=400, espaco_em=0.0) -> list[str]:
    """Quebra gulosa de linhas por palavra."""
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if atual and medir(teste, tamanho, familia, peso, espaco_em) > largura_max:
            linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    if atual:
        linhas.append(atual)
    return linhas


def fonte_css(usos: dict[tuple[str, int], str]) -> str:
    """@font-face com cada fonte reduzida às letras usadas, em woff2 base64.
    `usos` = {(família, peso): texto que usa essa fonte}."""
    blocos = []
    for (familia, peso), texto in sorted(usos.items()):
        if not texto:
            continue
        opcoes = Options()
        opcoes.flavor = "woff2"
        opcoes.layout_features = []  # sem kerning nem ligaduras: a medição é por avanço
        opcoes.name_IDs = []
        opcoes.notdef_outline = False
        sub = Subsetter(opcoes)
        fonte = _abrir(familia, peso)
        sub.populate(text=texto + " ")
        sub.subset(fonte)
        fonte.flavor = "woff2"
        saida = io.BytesIO()
        fonte.save(saida)
        dados = base64.b64encode(saida.getvalue()).decode()
        blocos.append(
            f"@font-face{{font-family:{familia};font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{dados}) format('woff2')}}"
        )
    return "".join(blocos)


# ---------------------------------------------------------------- texto
def esc(texto: str) -> str:
    return escape(texto, {'"': "&quot;"})


class Textos:
    """Junta o texto usado em cada fonte enquanto o SVG é montado, para o
    subconjunto da fonte ter exatamente essas letras."""

    def __init__(self):
        self.usos: dict[tuple[str, int], str] = {}

    def usar(self, texto: str, familia: str, peso: int) -> str:
        chave = (familia, peso)
        atual = self.usos.get(chave, "")
        novos = "".join(sorted(set(texto) - set(atual)))
        self.usos[chave] = atual + novos
        return texto

    def css(self) -> str:
        return fonte_css(self.usos)

    def texto(self, x, y, conteudo, *, tamanho, familia="SG", peso=400, cor=TEXT, espaco_em=0.0,
              ancora="start", classe="", extra="", maiusculas=False) -> str:
        if maiusculas:
            conteudo = conteudo.upper()
        self.usar(conteudo, familia, peso)
        ls = f' letter-spacing="{espaco_em * tamanho:.3f}"' if espaco_em else ""
        cls = f' class="{classe}"' if classe else ""
        return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{familia}" font-weight="{peso}" '
                f'font-size="{tamanho}"{ls} fill="{cor}" text-anchor="{ancora}"{cls}{extra}>{esc(conteudo)}</text>')

    def mono(self, x, y, conteudo, *, tamanho=12, peso=400, cor=TEXT_3, ancora="start", classe="", extra="") -> str:
        """Anotação em JetBrains Mono, caixa alta, como os rótulos do portfólio."""
        return self.texto(x, y, conteudo, tamanho=tamanho, familia="JB", peso=peso, cor=cor, espaco_em=0.06,
                          ancora=ancora, classe=classe, extra=extra, maiusculas=True)


# ---------------------------------------------------------------- formas
def seta(x: float, y: float, tamanho: float = 12, cor: str = TEXT, espessura: float = 1.6, classe: str = "") -> str:
    """↗ desenhada (as fontes do site não têm o glifo). (x, y) = canto inferior esquerdo."""
    t = tamanho
    cls = f' class="{classe}"' if classe else ""
    return (f'<path{cls} d="M{x:.2f} {y:.2f} L{x + t:.2f} {y - t:.2f} M{x + t * 0.3:.2f} {y - t:.2f} '
            f'L{x + t:.2f} {y - t:.2f} L{x + t:.2f} {y - t * 0.7:.2f}" fill="none" stroke="{cor}" '
            f'stroke-width="{espessura}" stroke-linecap="square"/>')


def ponto_vivo(cx: float, cy: float, r: float = 3.5) -> str:
    """O ponto verde de "disponível": pulsa devagar (ao vivo)."""
    return f'<circle class="vivo" cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" fill="{SIGNAL}"/>'


LOGO_BARRAS = [
    "3.5,18 8.7,18 13.7,46 8.5,46",
    "20.5,18 25.7,18 20.7,46 15.5,46",
    "27.5,18 32.7,18 37.7,46 32.5,46",
    "44.5,18 49.7,18 44.7,46 39.5,46",
]

# ---------------------------------------------------------------- CSS-base
CSS_BASE = f"""
text{{font-kerning:none;text-rendering:geometricPrecision}}
.vivo{{animation:vivo 2.4s ease-in-out infinite}}
@keyframes vivo{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.estatico{{display:none}}
@media (prefers-reduced-motion:reduce){{
  *{{animation:none!important}}
  .animado{{display:none}}
  .estatico{{display:inline}}
}}
"""


def svg(largura: float, altura: float, corpo: str, textos: Textos, css: str = "", titulo: str = "", fundo: str | None = INK) -> str:
    """Monta o documento SVG final com as fontes embutidas."""
    rotulo = f"<title>{esc(titulo)}</title>" if titulo else ""
    bg = f'<rect width="{largura}" height="{altura}" fill="{fundo}"/>' if fundo else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}" role="img"'
        f'{f" aria-label={chr(34)}{esc(titulo)}{chr(34)}" if titulo else ""}>'
        f"{rotulo}<style>{textos.css()}{CSS_BASE}{css}</style>{bg}{corpo}</svg>"
    )


def salvar(nome: str, conteudo: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    caminho = ASSETS / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho
