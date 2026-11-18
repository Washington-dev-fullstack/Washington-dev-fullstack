"""Gera os SVGs fixos do README (nome, projeto, contato, rodapé e botões).

Uso:  python ferramentas/gerar.py            (todos)
      python ferramentas/gerar.py capa.svg   (só os citados)
O gráfico de contribuições é gerado à parte, todo dia, por contribuicoes.py.

Animação leve: transform, opacity e o deslocamento do traço (stroke-dashoffset,
que só repinta o fio). Recortes que precisam andar juntos usam SMIL. Nada de
filtro ou desfoque. Com "reduzir movimento", cada SVG mostra um quadro parado
(.animado some, .estatico aparece).
"""
from __future__ import annotations

import base64
import io
import math
import random
from pathlib import Path

from PIL import Image

import fios as F
from luz import CSS_DESENHA, VELOCIDADE, camadas_cometa, cometas, fio_divisor
from identidade import (
    AMBAR, AMBAR_CLARO, CORAL, EASE_SAIDA, FIO, FIO_FORTE, LARGURA as W, MARGEM as M, NOITE, NOITE_2,
    SPLINE_SAIDA, SPLINE_SUAVE, TEXTO, TEXTO_2, TEXTO_3, Textos, altura_maiuscula, medir, ponto_vivo, salvar,
    seta, svg,
)

PASTA = Path(__file__).resolve().parent
CAPTURAS = PASTA / "capturas"
CONTEUDO = W - 2 * M

CSS_ENTRA = (f".entra{{animation:entra 1s {EASE_SAIDA} both}}"
             "@keyframes entra{from{opacity:0;transform:translateY(8px)}}"
             "@keyframes aparece{from{opacity:0}}")


def entra(atraso: float) -> str:
    """Classe + atraso da entrada padrão (sobe 8px e aparece)."""
    return f' class="entra" style="animation-delay:{atraso:.2f}s"'


def tecido(linhas: list[F.Linha], altura: float, rnd: random.Random, *, caixa_letras: tuple[float, float, float, float],
           n_pulsos: int = 26, dsep: float = 2.5, inicio: float = 0.25, duracao: float = 2.4,
           brilho: tuple[float, float] | None = None) -> tuple[str, str]:
    """Texto tecido por fios: o vento (fios de fora, quase invisíveis), o texto (fios
    densos dentro das letras, que chegam numa frente ondulada) e pulsos de luz que
    acendem ao atravessar as letras. Devolve (svg, css)."""
    css = []
    campo = F.Campo()
    m = F.mascara(linhas, W, altura)
    dentro_letras = F.dentro_da_mascara(m)
    fios_dentro = F.tecer(campo, dentro_letras, caixa_letras, dsep, passo=0.6, borda_exata=True, comprimento_min=1.5)
    fios_fora = F.tecer(campo, lambda x, y: -30 <= x <= W + 30 and -10 <= y <= altura + 10,
                        (-30, -10, W + 30, altura + 10), 9.0, passo=1.2, comprimento_min=40, semente=3)

    # os fios de fora que mais atravessam letras levam os pulsos de luz
    def dentro_px(fio: F.Fio) -> float:
        return sum(1 for p in fio if dentro_letras(*p)) * 1.2
    candidatos = sorted(fios_fora, key=dentro_px, reverse=True)
    pulsos = [f for f in candidatos[:n_pulsos * 2 + 8] if dentro_px(f) > 30]
    rnd.shuffle(pulsos)
    pulsos = pulsos[:n_pulsos]

    dentro_txt = F.caminho(F.enxugar(f, 0.1) for f in fios_dentro)
    fora_txt = F.caminho(F.enxugar(f, 0.15) for f in fios_fora)
    # o traço da luz pode ser mais enxuto que o fio: 0,3 px de desvio não se vê sob um traço de 1 px
    lista_p, css_p = cometas([F.enxugar(f, 0.3) for f in pulsos], rnd, prefixo="p")
    css.append(css_p)

    x_l0, _, x_l1, _ = caixa_letras
    corpo = ["<defs>"]
    if brilho:
        corpo.append(f'<radialGradient id="brilho" cx="{brilho[0]:.0f}" cy="{brilho[1]:.0f}" r="460" gradientUnits="userSpaceOnUse">'
                     f'<stop offset="0" stop-color="{AMBAR}" stop-opacity=".10"/>'
                     f'<stop offset="1" stop-color="{AMBAR}" stop-opacity="0"/></radialGradient>')
    corpo.append(
        f'<linearGradient id="tinta" x1="{x_l0:.0f}" x2="{x_l1:.0f}" y1="0" y2="0" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#ffd38f"/><stop offset=".55" stop-color="{AMBAR}"/><stop offset="1" stop-color="{CORAL}"/></linearGradient>'
        f'<clipPath id="letras">{F.contornos(linhas)}</clipPath>'
        f'<path id="dentro" d="{dentro_txt}"/></defs>')
    if brilho:
        corpo.append(f'<rect width="{W}" height="{altura}" fill="url(#brilho)"/>')

    # vento: os fios de fora, quase invisíveis
    corpo.append(f'<g class="vento" fill="none" stroke="{TEXTO}" stroke-width="1" stroke-opacity=".085">'
                 f'<path d="{fora_txt}"/></g>')
    css.append(".vento{animation:aparece 2.4s ease-out .1s both}")

    # um véu âmbar bem leve dentro das letras: o texto se lê mesmo onde os fios rareiam
    corpo.append(f'<rect width="{W}" height="{altura}" fill="{AMBAR}" fill-opacity=".06" clip-path="url(#letras)"/>')

    # o texto tecido chega com uma frente de vento ondulada, da esquerda, que acende os fios ao passar
    def onda(y: float) -> float:
        return 26 * math.sin(y * 0.045 + 1.2) + 12 * math.sin(y * 0.11)
    ys = [i * 8 for i in range(int(altura) // 8 + 2)]
    largo = W + 160
    frente = " ".join(f"{onda(y):.1f},{y}" for y in ys)
    varre = f"-{largo},0 {frente} -{largo},{ys[-1]}"
    faixa = (frente + " " + " ".join(f"{onda(y) - 90:.1f},{y}" for y in reversed(ys)))
    ida = f"-40 0;{largo} 0"
    tempo = (f'dur="{duracao}s" begin="{inicio}s" fill="freeze" calcMode="spline" keyTimes="0;1" '
             f'keySplines="{SPLINE_SUAVE}"')
    corpo.append(
        '<g class="animado">'
        f'<clipPath id="varre"><polygon points="{varre}" transform="translate(-40 0)">'
        f'<animateTransform attributeName="transform" type="translate" values="{ida}" {tempo}/></polygon></clipPath>'
        f'<clipPath id="faixa"><polygon points="{faixa}" transform="translate(-40 0)">'
        f'<animateTransform attributeName="transform" type="translate" values="{ida}" {tempo}/></polygon></clipPath>'
        '<use href="#dentro" clip-path="url(#varre)" fill="none" stroke="url(#tinta)" stroke-width="1" stroke-opacity=".9"/>'
        f'<use href="#dentro" clip-path="url(#faixa)" fill="none" stroke="{AMBAR_CLARO}" stroke-width="1.3"/>'
        "</g>"
        '<use class="estatico" href="#dentro" fill="none" stroke="url(#tinta)" stroke-width="1" stroke-opacity=".9"/>'
    )

    # pulsos: um rastro fraco no vento; ao atravessar as letras, a luz acende (halo + rastro + ponta)
    fora = camadas_cometa("p", lista_p, [
        ("cauda", f'stroke="{AMBAR}" stroke-opacity=".22" stroke-width="1.2"'),
        ("cabeca", f'stroke="{AMBAR}" stroke-opacity=".6" stroke-width="1.4"'),
    ])
    dentro = camadas_cometa("p", lista_p, [
        ("cauda", f'stroke="{AMBAR}" stroke-opacity=".16" stroke-width="7"'),
        ("cauda", f'stroke="{AMBAR_CLARO}" stroke-opacity=".6" stroke-width="1.6"'),
        ("cabeca", 'stroke="#fff6e6" stroke-width="2.2"'),
    ])
    corpo.append(f'<g class="pulsos" fill="none" stroke-linecap="round">{fora}'
                 f'<g clip-path="url(#letras)">{dentro}</g></g>')
    css.append(f".pulsos{{animation:aparece 1.2s ease-out {inicio + duracao - 0.4:.2f}s both}}")
    return "".join(corpo), "".join(css)


# ================================================================ NOME
def capa() -> str:
    t = Textos()
    rnd = random.Random(11)
    peso = 700
    tam = CONTEUDO / medir("WASHINGTON", 1, peso)
    cap = altura_maiuscula(peso) * tam
    y1 = 76 + cap
    y2 = y1 + 0.84 * tam
    altura = round(y2 + 82)
    linhas = [("WASHINGTON", M, y1, tam, peso, 0.0), ("GABRIEL", M, y2, tam, peso, 0.0)]

    trama, css = tecido(linhas, altura, rnd, caixa_letras=(M - 4, y1 - cap - 4, W - M + 4, y2 + 4),
                        brilho=(W * 0.42, (y1 + y2) / 2 - cap / 2))
    corpo = [trama]

    # ao lado de GABRIEL: quem é, e o status
    x = M + medir("GABRIEL", tam, peso) + 44
    topo = y2 - cap
    corpo.append(t.texto(x, topo + 17, "Desenvolvedor full stack", tamanho=20, peso=600, extra=entra(1.6)))
    corpo.append(t.texto(x, topo + 41, "em formação, de Hortolândia (SP).", tamanho=16, cor=TEXTO_2, extra=entra(1.7)))
    corpo.append(f'<g{entra(1.85)}>{ponto_vivo(x + 4, y2 - 5)}'
                 f'{t.texto(x + 17, y2, "Disponível para trabalho", tamanho=15, peso=500, cor=TEXTO_2)}</g>')

    return svg(W, altura, "".join(corpo), t, CSS_ENTRA + css,
               titulo="Washington Gabriel — desenvolvedor full stack em formação, de Hortolândia (SP). "
                      "Disponível para trabalho.")


# ================================================================ PROJETO
def _imagem(nome: str, largura: int = 1100, recorte_topo: int = 52) -> str:
    """Captura da demo → webp em data URI (o SVG como imagem só aceita imagens embutidas)."""
    img = Image.open(CAPTURAS / f"{nome}.png").convert("RGB")
    img = img.crop((0, recorte_topo, img.width, img.height))  # tira a faixa "Demonstração"
    img = img.resize((largura, round(largura * img.height / img.width)), Image.LANCZOS)
    saida = io.BytesIO()
    img.save(saida, "WEBP", quality=76, method=6)
    return "data:image/webp;base64," + base64.b64encode(saida.getvalue()).decode()


def _smil(atributo: str, quadros: list[tuple[float, str]], D: float, *, suaves: set[int] = frozenset(),
          tipo: str = "", inicio: float = 0.6) -> str:
    """Animação SMIL em laço a partir de (segundo, valor). Os trechos em `suaves`
    (índice do quadro onde o trecho começa) usam a curva de saída; o resto é linear."""
    tempos = ";".join(f"{s / D:.4f}" for s, _ in quadros)
    valores = ";".join(v for _, v in quadros)
    curvas = ";".join(SPLINE_SAIDA if i in suaves else "0 0 1 1" for i in range(len(quadros) - 1))
    elemento = "animateTransform" if tipo else "animate"
    extra = f' type="{tipo}"' if tipo else ""
    return (f'<{elemento} attributeName="{atributo}"{extra} values="{valores}" keyTimes="{tempos}" '
            f'calcMode="spline" keySplines="{curvas}" dur="{D}s" begin="{inicio}s" repeatCount="indefinite"/>')


def projeto() -> str:
    t = Textos()
    rnd = random.Random(5)
    css, corpo = [CSS_ENTRA, CSS_DESENHA], []

    # cabeçalho
    corpo.append(t.texto(M, 58, "Projeto em destaque", tamanho=15, peso=500, cor=TEXTO_3))
    status = "No ar no GitHub Pages"
    largura_status = medir(status, 15, 500)
    corpo.append(ponto_vivo(W - M - largura_status - 13, 53))
    corpo.append(t.texto(W - M, 58, status, tamanho=15, peso=500, cor=TEXTO_2, ancora="end"))
    corpo.append(t.texto(M - 2, 120, "Gemóvel", tamanho=54, peso=700))
    desc = ("Gestão de imóveis de aluguel por temporada: reservas, hóspedes, agenda e as tarefas de limpeza e "
            "manutenção da equipe. Painel do administrador no computador e app da equipe no celular.")
    par, y = t.paragrafo(desc, M, 160, CONTEUDO, 16, 25)
    corpo.append(par)

    # a tela: Visão geral por baixo; a Agenda entra tecida, faixa por faixa, e sai do mesmo jeito
    fx, fy, fw = float(M), y + 38, float(CONTEUDO)
    fh = fw * 948 / 1600
    r = 12
    corpo.append(
        "<defs>"
        f'<image id="i0" x="{fx}" y="{fy:.2f}" width="{fw}" height="{fh:.2f}" preserveAspectRatio="xMidYMid slice" href="{_imagem("visao-geral")}"/>'
        f'<image id="i1" x="{fx}" y="{fy:.2f}" width="{fw}" height="{fh:.2f}" preserveAspectRatio="xMidYMid slice" href="{_imagem("agenda")}"/>'
        f'<clipPath id="tela"><rect x="{fx}" y="{fy:.2f}" width="{fw}" height="{fh:.2f}" rx="{r}"/></clipPath>'
        "</defs>"
    )
    n, D, mov, passo = 16, 14.0, 0.9, 0.045
    a0, b0 = 5.0, 11.8
    h = fh / n
    faixas, lancadeiras = [], []
    eps = 0.02
    for i in range(n):
        a, b = a0 + i * passo, b0 + i * passo
        yi = fy + i * h
        faixas.append(
            f'<rect x="{fx}" y="{yi:.2f}" width="{fw}" height="{h + 0.6:.2f}" transform="translate({-fw} 0)">'
            + _smil("transform", [(0, f"{-fw} 0"), (a, f"{-fw} 0"), (a + mov, "0 0"), (b, "0 0"),
                                  (b + mov, f"{fw} 0"), (D, f"{fw} 0")], D, suaves={1, 3}, tipo="translate")
            + "</rect>")
        # a "lançadeira": um fio de luz na borda da faixa enquanto ela corre
        lancadeiras.append(
            f'<line x1="{fx}" y1="{yi:.2f}" x2="{fx}" y2="{yi + h:.2f}" opacity="0">'
            + _smil("transform", [(0, "0 0"), (a, "0 0"), (a + mov, f"{fw} 0"), (a + mov + eps, "0 0"), (b, "0 0"),
                                  (b + mov, f"{fw} 0"), (b + mov + eps, "0 0"), (D, "0 0")], D, suaves={1, 4},
                    tipo="translate")
            + _smil("opacity", [(0, "0"), (a - eps, "0"), (a, "1"), (a + mov * 0.7, "1"), (a + mov, "0"),
                                (b - eps, "0"), (b, "1"), (b + mov * 0.7, "1"), (b + mov, "0"), (D, "0")], D)
            + "</line>")
    corpo.append(
        f'<rect x="{fx - 1}" y="{fy - 1:.2f}" width="{fw + 2}" height="{fh + 2:.2f}" rx="{r + 1}" fill="{NOITE_2}"/>'
        f'<g clip-path="url(#tela)"><use href="#i0"/>'
        f'<g class="animado"><clipPath id="trama">{"".join(faixas)}</clipPath>'
        f'<use href="#i1" clip-path="url(#trama)"/>'
        f'<g stroke="{AMBAR_CLARO}" stroke-width="2">{"".join(lancadeiras)}</g></g></g>'
    )

    # a moldura é um fio: a luz dá a volta na tela, devagar
    k = 0.5523 * r  # aproximação do arco por Bézier
    x0, y0, x1, y1 = fx, fy, fx + fw, fy + fh
    contorno = (f"M{x0 + r:.1f} {y0:.1f}H{x1 - r:.1f}C{x1 - r + k:.1f} {y0:.1f} {x1:.1f} {y0 + r - k:.1f} {x1:.1f} {y0 + r:.1f}"
                f"V{y1 - r:.1f}C{x1:.1f} {y1 - r + k:.1f} {x1 - r + k:.1f} {y1:.1f} {x1 - r:.1f} {y1:.1f}"
                f"H{x0 + r:.1f}C{x0 + r - k:.1f} {y1:.1f} {x0:.1f} {y1 - r + k:.1f} {x0:.1f} {y1 - r:.1f}"
                f"V{y0 + r:.1f}C{x0:.1f} {y0 + r - k:.1f} {x0 + r - k:.1f} {y0:.1f} {x0 + r:.1f} {y0:.1f}Z")
    perimetro = 2 * (fw + fh) - (8 - 2 * math.pi) * r
    cauda, cabeca = 260 / perimetro * 1000, 50 / perimetro * 1000
    corpo.append(
        f'<path d="{contorno}" fill="none" stroke="{FIO_FORTE}"/>'
        f'<g class="volta" fill="none" stroke-linecap="round">'
        f'<path d="{contorno}" pathLength="1000" stroke="{AMBAR}" stroke-opacity=".45" stroke-width="1.4" '
        f'stroke-dasharray="0 {1000 - cauda:.1f} {cauda:.1f} 0"/>'
        f'<path d="{contorno}" pathLength="1000" stroke="{AMBAR_CLARO}" stroke-width="2" '
        f'stroke-dasharray="0 {1000 - cabeca:.1f} {cabeca:.1f} 0"/></g>'
    )
    css.append(f".volta{{stroke-dashoffset:-180;animation:corre {perimetro / VELOCIDADE:.2f}s linear infinite}}"
               "@keyframes corre{from{stroke-dashoffset:0}to{stroke-dashoffset:-1000}}")

    # legenda que troca junto com a tela
    yl = fy + fh + 32
    for texto, quadros in (
        ("Visão geral", [(0, "1"), (a0 + 0.2, "1"), (a0 + 0.6, "0"), (b0 + 0.5, "0"), (b0 + 0.9, "1"), (D, "1")]),
        ("Agenda", [(0, "0"), (a0 + 0.5, "0"), (a0 + 0.9, "1"), (b0 + 0.2, "1"), (b0 + 0.6, "0"), (D, "0")]),
    ):
        corpo.append(f'<g class="animado" opacity="{quadros[0][1]}">'
                     f'<line x1="{M}" y1="{yl - 5}" x2="{M + 18}" y2="{yl - 5}" stroke="{AMBAR}" stroke-width="1.5"/>'
                     f'{t.texto(M + 28, yl, texto, tamanho=15, peso=500, cor=TEXTO_2)}{_smil("opacity", quadros, D)}</g>')
    corpo.append(f'<g class="estatico"><line x1="{M}" y1="{yl - 5}" x2="{M + 18}" y2="{yl - 5}" stroke="{AMBAR}" '
                 f'stroke-width="1.5"/>{t.texto(M + 28, yl, "Visão geral", tamanho=15, peso=500, cor=TEXTO_2)}</g>')
    corpo.append(t.texto(W - M, yl, "Demo pública, com contas de exemplo", tamanho=15, cor=TEXTO_3, ancora="end"))

    # ficha, sob uma divisória de fio
    y = yl + 42
    divisor, css_div = fio_divisor(y, rnd, prefixo="d", atraso=0.4)
    corpo.append(divisor)
    css.append(css_div)
    ficha = [("Ano", "2026"), ("Tipo", "Sistema web"), ("Stack", "Python · Flask · MySQL · JS"),
             ("Equipe", "Em dupla com Arthur Gazzoli")]
    colunas = [M, M + 122, M + 282, W - M - medir(ficha[3][1], 16, 500)]
    for x, (rotulo, valor) in zip(colunas, ficha):
        corpo.append(t.texto(x, y + 38, rotulo, tamanho=13, peso=500, cor=TEXTO_3))
        corpo.append(t.texto(x, y + 62, valor, tamanho=16, peso=500))
    altura = round(y + 96)

    return svg(W, altura, "".join(corpo), t, "".join(css),
               titulo="Projeto em destaque: Gemóvel, gestão de imóveis de aluguel por temporada, no ar no GitHub Pages. "
                      "2026, Python, Flask, MySQL e JavaScript, em dupla com Arthur Gazzoli.")


# ================================================================ BOTÕES
def botao(rotulo: str, primario: bool = False) -> str:
    """Pílula. A principal é âmbar (a luz); as outras são um fio sobre a noite."""
    t = Textos()
    tam = 16
    largura_txt = medir(rotulo, tam, 700)
    largura = round(largura_txt + 56 + 22)
    altura = 52
    fundo, borda, cor = (AMBAR, AMBAR, NOITE) if primario else (NOITE, FIO_FORTE, TEXTO)
    corpo = [f'<rect x="1" y="1" width="{largura - 2}" height="{altura - 2}" rx="25" fill="{fundo}" '
             f'stroke="{borda}" stroke-width="1.5"/>',
             t.texto(28, 31.5, rotulo, tamanho=tam, peso=700, cor=cor),
             seta(28 + largura_txt + 12, 31, 10, cor, 1.8, classe="seta")]
    css = (".seta{animation:seta 3.6s ease-in-out infinite}"
           "@keyframes seta{0%,72%,100%{transform:translate(0,0)}82%{transform:translate(2.5px,-2.5px)}}")
    return svg(largura, altura, "".join(corpo), t, css, titulo=rotulo, fundo=None)


# ================================================================ CONTATO
def contato() -> str:
    t = Textos()
    rnd = random.Random(23)
    peso = 700
    frase = "Me chama."
    tam = 118
    cap = altura_maiuscula(peso) * tam
    y_frase = 98 + cap
    y_div = y_frase + 54
    altura = round(y_div + 118)
    linhas = [(frase, M - 4, y_frase, tam, peso, 0.0)]

    corpo = [t.texto(M, 64, "Tem uma vaga ou uma ideia?", tamanho=30, peso=600, extra=entra(0.2))]
    trama, css = tecido(linhas, altura, rnd, caixa_letras=(M - 8, y_frase - tam, M + medir(frase, tam, peso) + 4, y_frase + 4),
                        n_pulsos=14, inicio=0.5, duracao=2.0, brilho=(W * 0.35, y_frase - cap / 2))
    corpo.insert(0, trama)

    divisor, css_div = fio_divisor(y_div, rnd, prefixo="d", atraso=1.2)
    corpo.append(divisor)
    y = y_div + 56
    corpo.append(t.texto(M, y, "washington.gab.dev@gmail.com", tamanho=28, peso=600, extra=entra(1.5)))
    corpo.append(t.texto(M, y + 32, "Estou em busca da minha primeira oportunidade. Respondo rápido.",
                         tamanho=16, cor=TEXTO_2, extra=entra(1.6)))
    status = "Disponível para trabalho"
    corpo.append(f'<g{entra(1.7)}>{ponto_vivo(W - M - medir(status, 15, 500) - 13, y - 5)}'
                 f'{t.texto(W - M, y, status, tamanho=15, peso=500, cor=TEXTO_2, ancora="end")}</g>')
    corpo.append(t.texto(W - M, y + 32, "Hortolândia, SP · UTC−3", tamanho=15, cor=TEXTO_3, ancora="end", extra=entra(1.8)))

    return svg(W, altura, "".join(corpo), t, CSS_ENTRA + CSS_DESENHA + css + css_div,
               titulo="Tem uma vaga ou uma ideia? Me chama. E-mail: washington.gab.dev@gmail.com. "
                      "Disponível para trabalho, Hortolândia (SP).")


# ================================================================ RODAPÉ
def rodape() -> str:
    t = Textos()
    rnd = random.Random(31)
    altura = 112
    corpo, css = [], [CSS_DESENHA]
    # o vento do topo volta aqui, mais ralo: a bio fecha com os mesmos fios com que abre
    vento = F.tecer(F.Campo(), lambda x, y: -30 <= x <= W + 30 and -10 <= y <= altura + 10,
                    (-30, -10, W + 30, altura + 10), 11.0, passo=1.2, comprimento_min=40, semente=9)
    corpo.append(f'<path d="{F.caminho(F.enxugar(f, 0.15) for f in vento)}" fill="none" stroke="{TEXTO}" '
                 f'stroke-opacity=".06"/>')
    divisor, css_div = fio_divisor(42, rnd, prefixo="d", atraso=0.2)
    corpo.append(divisor)
    css.append(css_div)
    corpo.append(t.texto(M, 82, "Portfólio completo chegando em breve.", tamanho=17, peso=600, cor=TEXTO_2))
    corpo.append(t.texto(W - M, 82, "© 2026 Washington Gabriel", tamanho=15, cor=TEXTO_3, ancora="end"))
    return svg(W, altura, "".join(corpo), t, "".join(css),
               titulo="Portfólio completo chegando em breve. © 2026 Washington Gabriel.")


def main(apenas: set[str] | None = None):
    arquivos = {
        "capa.svg": capa,
        "projeto.svg": projeto,
        "contato.svg": contato,
        "rodape.svg": rodape,
        "botao-demo.svg": lambda: botao("Abrir o Gemóvel", primario=True),
        "botao-codigo.svg": lambda: botao("Ver o código"),
        "botao-email.svg": lambda: botao("E-mail", primario=True),
        "botao-linkedin.svg": lambda: botao("LinkedIn"),
        "botao-whatsapp.svg": lambda: botao("WhatsApp"),
    }
    for nome, gerar in arquivos.items():
        if apenas and nome not in apenas:
            continue
        caminho = salvar(nome, gerar())
        print(f"{nome:22} {caminho.stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    import sys
    main(set(sys.argv[1:]) or None)
