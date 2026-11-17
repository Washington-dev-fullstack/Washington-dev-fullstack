"""Gera os SVGs fixos do README (capa, projeto, contato, rodapé e botões).

Uso:  python ferramentas/gerar.py
O gráfico de contribuições é gerado à parte, todo dia, por contribuicoes.py.

Animação leve: só transform e opacity (CSS) e, onde é preciso sincronizar
recortes, SMIL. Nada de filtro ou desfoque. Com "reduzir movimento", cada SVG
mostra o estado final, parado (.animado some, .estatico aparece).
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from identidade import (
    EASE_RENDER, INK, INK_2, LARGURA as W, LINE, LINE_STRONG, LOGO_BARRAS, MARGEM as M, PAPER,
    PAPER_INK, SIGNAL, SPLINE_RENDER, TEXT, TEXT_2, TEXT_3, VAZADO, Textos, altura_maiuscula,
    esc, medir, ponto_vivo, quebrar, salvar, seta, svg,
)

PASTA = Path(__file__).resolve().parent
CAPTURAS = PASTA / "capturas"
CAP = altura_maiuscula("SG", 700)
CONTEUDO = W - 2 * M  # 800

LINK_DEMO = "https://washington-dev-fullstack.github.io/gemovel-integrative-project/"


def tamanho_para(texto: str, largura: float, peso: int = 700, espaco_em: float = -0.05) -> float:
    """Tamanho de fonte para o texto ocupar exatamente a largura (sem a folga final)."""
    um = medir(texto, 1, "SG", peso, espaco_em) - espaco_em
    return largura / um


def letras(t: Textos, texto: str, x0: float, y: float, tamanho: float, *, vazado: bool, classe: str = "",
           atraso0: float = 0.0, passo: float = 0.0, espaco_em: float = -0.05) -> str:
    """Uma <text> por letra, posicionadas pela medição (permite a entrada letra a letra)."""
    t.usar(texto, "SG", 700)
    pintura = (f'fill="none" stroke="{VAZADO}" stroke-width="1.5"' if vazado else f'fill="{TEXT}"')
    partes, x = [], x0
    for i, c in enumerate(texto):
        estilo = f' style="animation-delay:{atraso0 + i * passo:.3f}s"' if classe else ""
        cls = f' class="{classe}"' if classe else ""
        partes.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="SG" font-weight="700" '
                      f'font-size="{tamanho:.2f}" {pintura}{cls}{estilo}>{esc(c)}</text>')
        x += medir(c, tamanho, "SG", 700, espaco_em)
    return "".join(partes)


def palavras(t: Textos, linhas: list[str], x0: float, y0: float, tamanho: float, altura_linha: float, *,
             peso: int, espaco_em: float, classe: str, atraso0: float, passo: float) -> tuple[str, float]:
    """Uma <text> por palavra (para o preenchimento palavra a palavra). Devolve (svg, y final)."""
    partes, i, y = [], 0, y0
    espaco = medir(" ", tamanho, "SG", peso, espaco_em)
    for linha in linhas:
        x = x0
        for p in linha.split():
            t.usar(p, "SG", peso)
            partes.append(
                f'<text x="{x:.2f}" y="{y:.2f}" font-family="SG" font-weight="{peso}" font-size="{tamanho}" '
                f'letter-spacing="{espaco_em * tamanho:.3f}" class="{classe}" '
                f'style="animation-delay:{atraso0 + i * passo:.2f}s">{esc(p)}</text>')
            x += medir(p, tamanho, "SG", peso, espaco_em) + espaco
            i += 1
        y += altura_linha
    return "".join(partes), y - altura_linha


def paragrafo(t: Textos, texto: str, x: float, y: float, largura: float, tamanho: float, altura_linha: float,
              cor: str = TEXT_2, peso: int = 400, classe: str = "", extra: str = "") -> tuple[str, float]:
    linhas = quebrar(texto, largura, tamanho, "SG", peso)
    partes = [t.texto(x, y + i * altura_linha, l, tamanho=tamanho, peso=peso, cor=cor, classe=classe, extra=extra)
              for i, l in enumerate(linhas)]
    return "".join(partes), y + (len(linhas) - 1) * altura_linha


def linha_cabeca(t: Textos, y: float, esquerda: str, direita: str = "", vivo: bool = False, classe: str = "") -> str:
    """Rótulo de seção (mono, text-3) à esquerda e anotação à direita, com o ponto verde se ao vivo."""
    partes = [t.mono(M, y, esquerda, classe=classe)]
    if direita:
        partes.append(t.mono(W - M, y, direita, ancora="end", classe=classe))
        if vivo:
            largura = medir(direita.upper(), 12, "JB", 400, 0.06)
            partes.append(ponto_vivo(W - M - largura - 12, y - 4))
    return "".join(partes)


# ================================================================ CAPA
CODIGO_LENTE = [
    '<section id="inicio" class="hero">',
    '  <h1 class="hero-nome" aria-label="Washington Gabriel">',
    '    <span class="hero-linha vazado">Washington</span>',
    '    <span class="hero-linha">Gabriel</span>',
    '  </h1>',
    '  <p class="hero-frase">Full stack aprendiz.</p>',
    '</section>',
    '',
    '/* vazado = rascunho · sólido = entregue */',
    '.hero-nome {',
    "  font: 700 var(--fs-mega)/0.86 'Space Grotesk';",
    '  letter-spacing: -0.05em;',
    '}',
    '.vazado { color: transparent; -webkit-text-stroke: 1.5px; }',
    '.camada-fonte { clip-path: circle(var(--r) at var(--x) var(--y)); }',
    'gsap.from(nome.chars, { yPercent: 110, stagger: 0.03 });',
]


def capa() -> str:
    t = Textos()
    css, corpo = [], []

    # ---------- hero
    F = tamanho_para("WASHINGTON", CONTEUDO)
    y_nome_topo = 112
    y1 = y_nome_topo + CAP * F
    y2 = y1 + 0.86 * F
    subida = CAP * F * 1.18
    y_base = y2 + 58
    alt_hero = y_base + 74

    # grade de 12 colunas que "desenha" de cima para baixo
    for i in range(13):
        x = M + i * CONTEUDO / 12
        corpo.append(f'<line class="grade" x1="{x:.2f}" y1="0" x2="{x:.2f}" y2="{alt_hero:.0f}" '
                     f'style="animation-delay:{i * 0.04:.2f}s"/>')
    css.append(f".grade{{stroke:rgba(246,246,241,.055);stroke-width:1;transform-box:fill-box;transform-origin:top;"
               f"animation:grade 1.6s {EASE_RENDER} both}}@keyframes grade{{from{{transform:scaleY(0)}}}}")

    # logo: o W digitado barra a barra, com o cursor verde andando (como o preloader)
    tempos = [0.15 + i * 0.14 for i in range(4)]
    barras = "".join(f'<polygon class="barra" points="{p}" style="animation-delay:{tempos[i]:.2f}s"/>'
                     for i, p in enumerate(LOGO_BARRAS))
    corpo.append(f'<g transform="translate({M - 2} 22) scale(0.72)" fill="{TEXT}">{barras}'
                 f'<rect class="cursor-logo" x="53" y="33" width="8" height="13" fill="{SIGNAL}"/></g>')
    dur = 0.8
    pct = [f"{tm / dur * 100:.2f}%" for tm in tempos]
    css.append(
        ".barra{animation:aparece .01s linear both}@keyframes aparece{from{opacity:0}}"
        f".cursor-logo{{animation:cursorlogo {dur}s step-end both,pisca 1.06s step-end {dur + 0.4:.2f}s infinite}}"
        f"@keyframes cursorlogo{{0%{{transform:translateX(-49.5px)}}{pct[0]}{{transform:translateX(-38.3px)}}"
        f"{pct[1]}{{transform:translateX(-26.3px)}}{pct[2]}{{transform:translateX(-14.3px)}}"
        f"{pct[3]},100%{{transform:translateX(0)}}}}"
        "@keyframes pisca{0%{opacity:1}50%{opacity:0}}"
    )

    css.append(f".entra{{animation:entra 1s {EASE_RENDER} both}}"
               "@keyframes entra{from{opacity:0;transform:translateY(10px)}}")
    corpo.append(t.mono(M + 56, 50, "Portfólio / 2026", classe="entra", extra=' style="animation-delay:.9s"'))
    corpo.append(f'<g class="entra" style="animation-delay:1s">'
                 f'{linha_cabeca(t, 50, "", "Disponível para trabalho", vivo=True)}</g>')

    # nome: WASHINGTON vazado (rascunho) e GABRIEL sólido (entregue), subindo letra a letra
    for n, (palavra, y, vaz, atraso) in enumerate([("WASHINGTON", y1, True, 0.35), ("GABRIEL", y2, False, 0.55)]):
        topo = y - CAP * F - 0.1 * F
        corpo.append(f'<clipPath id="janela{n}"><rect x="0" y="{topo:.2f}" width="{W}" height="{CAP * F + 0.2 * F:.2f}"/></clipPath>')
        corpo.append(f'<g clip-path="url(#janela{n})">'
                     f'{letras(t, palavra, M, y, F, vazado=vaz, classe="letra", atraso0=atraso, passo=0.03)}</g>')
    css.append(f".letra{{animation:sobe 1.1s {EASE_RENDER} both}}"
               f"@keyframes sobe{{from{{transform:translateY({subida:.1f}px)}}}}")

    # a lente: um círculo que passeia pelo nome e mostra o "código" por trás, com os estados invertidos
    caminho = "M230,215 C340,120 580,130 690,200 C790,265 640,330 470,300 C300,272 110,300 230,215 Z"
    movimento = f'<animateMotion path="{caminho}" dur="22s" repeatCount="indefinite"/>'
    abre = (f'<animate attributeName="r" values="0;78" keyTimes="0;1" calcMode="spline" keySplines="{SPLINE_RENDER}" '
            f'begin="2.3s" dur="1.1s" fill="freeze"/>')
    # o código cobre toda a área do nome: duas colunas, a segunda começando no meio do bloco
    metade = len(CODIGO_LENTE) // 2
    codigo = "".join(
        t.texto(x, 104 + i * 15.5, CODIGO_LENTE[(i + desloc) % len(CODIGO_LENTE)], tamanho=10.5, familia="JB",
                peso=400, cor="rgba(246,246,241,.45)")
        for x, desloc in ((M, 0), (M + 410, metade))
        for i in range(len(CODIGO_LENTE) + 2) if CODIGO_LENTE[(i + desloc) % len(CODIGO_LENTE)]
    )
    inverso = (letras(t, "WASHINGTON", M, y1, F, vazado=False) + letras(t, "GABRIEL", M, y2, F, vazado=True))
    corpo.append(
        f'<g class="animado"><clipPath id="lente"><circle r="0">{abre}{movimento}</circle></clipPath>'
        f'<g clip-path="url(#lente)"><rect x="0" y="80" width="{W}" height="{y2 - 40:.0f}" fill="{INK_2}"/>'
        f'{codigo}{inverso}</g>'
        f'<circle r="0" fill="none" stroke="{LINE_STRONG}" stroke-width="1">{abre}{movimento}</circle></g>'
    )

    # base do hero: a frase e a localização
    frase, _ = paragrafo(t, "Full stack aprendiz. Crio interfaces que respondem, se movem e têm presença.",
                         M, y_base, 390, 17, 25, classe="entra", extra=' style="animation-delay:1.15s"')
    corpo.append(frase)
    corpo.append(t.mono(W - M, y_base, "Hortolândia, SP — Brasil", ancora="end", classe="entra",
                        extra=' style="animation-delay:1.25s"'))
    corpo.append(t.mono(W - M, y_base + 22, "Full-stack developer in training", ancora="end", cor=TEXT_2, classe="entra",
                        extra=' style="animation-delay:1.35s"'))

    # ---------- sobre: o manifesto se preenche palavra por palavra
    y = alt_hero + 34
    corpo.append(f'<line class="risco" x1="{M}" y1="{alt_hero:.1f}" x2="{W - M}" y2="{alt_hero:.1f}" stroke="{LINE}"/>')
    css.append(f".risco{{transform-box:fill-box;transform-origin:left;animation:risco 1.4s {EASE_RENDER} 1.4s both}}"
               "@keyframes risco{from{transform:scaleX(0)}}")
    corpo.append(linha_cabeca(t, y + 22, "01 / Sobre", "Manifesto"))
    manifesto = ("Eu não faço páginas que parecem template. Construo experiências onde design e código são a "
                 "mesma decisão — e cada detalhe tem um motivo.")
    tam = 35
    linhas = quebrar(manifesto, CONTEUDO, tam, "SG", 500, -0.035)
    trecho, y_fim = palavras(t, linhas, M, y + 84, tam, tam * 1.14, peso=500, espaco_em=-0.035,
                             classe="palavra", atraso0=2.0, passo=0.09)
    corpo.append(trecho)
    css.append(f".palavra{{fill:{TEXT};stroke:rgba(246,246,241,.38);stroke-width:1;"
               "animation:preenche 15s ease-in-out infinite both}"
               "@keyframes preenche{0%{fill-opacity:0}4%{fill-opacity:1}86%{fill-opacity:1}92%,100%{fill-opacity:0}}")

    # os três pilares
    y = y_fim + 62
    col = (CONTEUDO - 2 * 28) / 3
    pilares = [
        ("01", "Base técnica", "Técnico em Informática integrado ao Ensino Médio na UNASP Hortolândia (2025–2027)."),
        ("02", "Curiosidade aplicada", "Python, DevArte, inglês e IA como ferramenta. Testar, quebrar, ajustar e publicar."),
        ("03", "Direção visual", "Interfaces com presença: interações que respondem a quem usa e layouts que respiram."),
    ]
    y_max = y
    for i, (num, titulo, texto) in enumerate(pilares):
        x = M + i * (col + 28)
        atraso = 2.2 + i * 0.12
        corpo.append(f'<line class="risco" x1="{x:.1f}" y1="{y:.1f}" x2="{x + col:.1f}" y2="{y:.1f}" '
                     f'stroke="{LINE_STRONG}" style="animation-delay:{atraso:.2f}s"/>')
        corpo.append(t.mono(x, y + 26, num))
        corpo.append(t.texto(x, y + 58, titulo, tamanho=20, peso=500, espaco_em=-0.03))
        par, yf = paragrafo(t, texto, x, y + 86, col - 8, 13.5, 20.5)
        corpo.append(par)
        y_max = max(y_max, yf)

    # ---------- faixa creme: a matéria-prima, inclinada, palavras alternando sólidas e vazadas
    y_faixa = y_max + 64
    alt_faixa = 118
    itens = ["HTML", "CSS", "JavaScript", "PHP", "MySQL", "Python", "Flask", "POO", "GSAP", "UX/UI", "C++"]
    tam_m = 62
    folga = 52
    base_m = y_faixa + alt_faixa / 2 + CAP * tam_m / 2
    partes_m, x = [], 0.0
    for _ in range(2):
        for i, item in enumerate(itens):
            rotulo = item.upper()
            t.usar(rotulo, "SG", 700)
            pintura = (f'fill="none" stroke="rgba(11,11,11,.55)" stroke-width="1.2"' if i % 2 else f'fill="{PAPER_INK}"')
            partes_m.append(f'<text x="{x:.2f}" y="{base_m:.2f}" font-family="SG" font-weight="700" font-size="{tam_m}" '
                            f'letter-spacing="{-0.05 * tam_m:.2f}" {pintura}>{esc(rotulo)}</text>')
            x += medir(rotulo, tam_m, "SG", 700, -0.05) + folga
    volta = x / 2
    corpo.append(
        f'<g transform="rotate(-1.2 {W / 2} {y_faixa + alt_faixa / 2:.1f})">'
        f'<rect x="-80" y="{y_faixa:.1f}" width="{W + 160}" height="{alt_faixa}" fill="{PAPER}"/>'
        f'<g class="trilho">{"".join(partes_m)}</g></g>'
    )
    css.append(f".trilho{{animation:trilho 34s linear infinite}}"
               f"@keyframes trilho{{to{{transform:translateX(-{volta:.2f}px)}}}}")

    altura = y_faixa + alt_faixa + 46
    return svg(W, round(altura), "".join(corpo), t, "".join(css),
               titulo="Washington Gabriel — full stack aprendiz. Portfólio / 2026, disponível para trabalho.")


# ================================================================ PROJETO
def _imagem(nome: str, recorte_topo: int = 52, largura: int = 1100, rascunho: bool = False) -> str:
    """Captura da demo → webp em data URI (o SVG como imagem só aceita imagens embutidas)."""
    img = Image.open(CAPTURAS / f"{nome}.png").convert("RGB")
    img = img.crop((0, recorte_topo, img.width, img.height))  # tira a faixa "Demonstração"
    img = img.resize((largura, round(largura * img.height / img.width)), Image.LANCZOS)
    if rascunho:
        img = ImageOps.grayscale(img).convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(0.55)
        img = ImageEnhance.Brightness(img).enhance(0.62)
    saida = io.BytesIO()
    img.save(saida, "WEBP", quality=70 if rascunho else 78, method=6)
    return "data:image/webp;base64," + base64.b64encode(saida.getvalue()).decode()


def projeto() -> str:
    t = Textos()
    css, corpo = [], []
    altura = 482
    corpo.append(f'<rect width="{W}" height="{altura}" fill="rgba(166,244,255,0.04)"/>')  # tom do projeto, como no site
    corpo.append(linha_cabeca(t, 50, "02 / Projeto em destaque", "Ao vivo · GitHub Pages", vivo=True))

    # moldura: o print nasce rascunho e "renderiza" num corte diagonal
    fx, fy, fw = 330.0, 84.0, 510.0
    fh = fw * 948 / 1600
    s = 70  # inclinação do corte "/"
    corpo.append(
        "<defs>"
        f'<image id="r0" x="{fx}" y="{fy}" width="{fw}" height="{fh:.2f}" preserveAspectRatio="xMidYMid slice" href="{_imagem("visao-geral", rascunho=True)}"/>'
        f'<image id="r1" x="{fx}" y="{fy}" width="{fw}" height="{fh:.2f}" preserveAspectRatio="xMidYMid slice" href="{_imagem("visao-geral")}"/>'
        f'<image id="r2" x="{fx}" y="{fy}" width="{fw}" height="{fh:.2f}" preserveAspectRatio="xMidYMid slice" href="{_imagem("agenda")}"/>'
        f'<clipPath id="moldura"><rect x="{fx}" y="{fy}" width="{fw}" height="{fh:.2f}"/></clipPath>'
        "</defs>"
    )
    grade = "".join(f'<line x1="{fx + i * fw / 12:.2f}" y1="{fy}" x2="{fx + i * fw / 12:.2f}" y2="{fy + fh:.2f}"/>'
                    for i in range(1, 12))
    grade += "".join(f'<line x1="{fx}" y1="{fy + i * fh / 6:.2f}" x2="{fx + fw}" y2="{fy + i * fh / 6:.2f}"/>'
                     for i in range(1, 6))

    D = 16.0  # ciclo: rascunho → visão geral → agenda → volta ao rascunho
    def kt(*segundos):  # segundos → keyTimes
        return ";".join(f"{x / D:.4f}" for x in segundos)
    escondido = f"{-(fw + s):.1f} 0"

    def corte(id_, entra, sai_fim=D):
        """Polígono com a borda direita em "/" que atravessa a moldura."""
        poly = (f"{fx - fw - 2 * s:.1f},{fy - 2} {fx + fw + s:.1f},{fy - 2} {fx + fw:.1f},{fy + fh + 2:.1f} "
                f"{fx - fw - 2 * s:.1f},{fy + fh + 2:.1f}")
        anim = (f'<animateTransform attributeName="transform" type="translate" '
                f'values="{escondido};{escondido};0 0;0 0" keyTimes="{kt(0, entra, entra + 1.3, sai_fim)}" '
                f'calcMode="spline" keySplines="0 0 1 1;{SPLINE_RENDER};0 0 1 1" dur="{D}s" begin="0.8s" repeatCount="indefinite"/>')
        borda = (f'<line x1="{fx + fw + s:.1f}" y1="{fy:.1f}" x2="{fx + fw:.1f}" y2="{fy + fh:.1f}" stroke="{SIGNAL}" stroke-width="2" opacity="0" transform="translate({escondido})">'
                 f'{anim}<animate attributeName="opacity" values="0;0;1;1;0;0" '
                 f'keyTimes="{kt(0, entra - 0.01, entra, entra + 1.0, entra + 1.3, D)}" dur="{D}s" begin="0.8s" repeatCount="indefinite"/></line>')
        return f'<clipPath id="{id_}"><polygon points="{poly}" transform="translate({escondido})">{anim}</polygon></clipPath>', borda

    c1, b1 = corte("corte1", 0.0)
    c2, b2 = corte("corte2", 7.0)
    some = (f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="{kt(0, 14.4, 15.3, D)}" '
            f'dur="{D}s" begin="0.8s" repeatCount="indefinite"/>')
    corpo.append(
        f'<rect x="{fx - 1}" y="{fy - 1}" width="{fw + 2}" height="{fh + 2:.2f}" fill="{INK_2}" stroke="{LINE}"/>'
        f'<use href="#r0"/>'
        f'<g stroke="rgba(246,246,241,.07)" stroke-width="1">{grade}</g>'
        f'<g class="animado">{c1}{c2}<g>{some}'
        f'<g clip-path="url(#corte1)"><use href="#r1"/></g>'
        f'<g clip-path="url(#corte2)"><use href="#r2"/></g></g>'
        f'<g clip-path="url(#moldura)">{b1}{b2}</g></g>'
        f'<g class="estatico"><use href="#r1"/></g>'
    )
    corpo.append(t.mono(fx + fw, fy - 10, "1600 × 948", tamanho=10, ancora="end", cor=TEXT_3,
                        classe="medida"))
    css.append(".medida{animation:medida 16s linear .8s infinite both}"
               "@keyframes medida{0%,4%{opacity:1}6%,92%{opacity:0}96%,100%{opacity:1}}")

    # legendas que trocam junto com a tela
    yl = fy + fh + 28
    legendas = [("Fig. 00 — Rascunho", "1;1;0;0;1;1", (0, 0.9, 1.3, 15.2, 15.6, D)),
                ("Fig. 01 — Visão geral", "0;0;1;1;0;0", (0, 0.9, 1.3, 7.4, 7.8, D)),
                ("Fig. 02 — Agenda", "0;0;1;1;0;0", (0, 7.4, 7.8, 15.2, 15.6, D))]
    for texto, valores, tempos in legendas:
        anim = (f'<animate attributeName="opacity" values="{valores}" keyTimes="{kt(*tempos)}" '
                f'dur="{D}s" begin="0.8s" repeatCount="indefinite"/>')
        t.usar(texto.upper(), "JB", 400)
        corpo.append(f'<g class="animado" opacity="{valores.split(";")[0]}">{t.mono(fx, yl, texto)}{anim}</g>')
    corpo.append(t.mono(fx, yl, "Fig. 01 — Visão geral", classe="estatico"))
    corpo.append(t.mono(fx + fw, yl, "Demo pública · contas de exemplo", ancora="end"))

    # informações do projeto
    tam_num = 96
    y_num = fy + CAP * tam_num
    t.usar("01", "SG", 700)
    corpo.append(
        '<linearGradient id="prisma" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#a6f4ff"/><stop offset=".38" stop-color="#cdbcff"/>'
        '<stop offset=".7" stop-color="#ffb8e3"/><stop offset="1" stop-color="#ffe2a6"/></linearGradient>'
        f'<text x="{M - 4}" y="{y_num:.2f}" font-family="SG" font-weight="700" font-size="{tam_num}" '
        f'letter-spacing="{-0.05 * tam_num:.2f}" fill="none" stroke="url(#prisma)" stroke-width="1.3">01</text>'
    )
    y = y_num + 54
    corpo.append(t.texto(M, y, "Gemóvel", tamanho=42, peso=700, espaco_em=-0.04))
    desc = ("Gestão de imóveis de aluguel por temporada: reservas, hóspedes, agenda e as tarefas de limpeza "
            "e manutenção da equipe. Painel do administrador no computador e app da equipe no celular.")
    par, y = paragrafo(t, desc, M, y + 34, 262, 14, 21)
    corpo.append(par)
    y += 30
    ficha = [("Ano", "2026"), ("Tipo", "Sistema web"), ("Stack", "Python · Flask · MySQL · JS"),
             ("Equipe", "Em dupla com Arthur Gazzoli")]
    for i, (dt, dd) in enumerate(ficha):
        yy = y + i * 25
        corpo.append(f'<line x1="{M}" y1="{yy - 16:.1f}" x2="{M + 262}" y2="{yy - 16:.1f}" stroke="{LINE}"/>')
        corpo.append(t.mono(M, yy, dt, tamanho=10.5))
        corpo.append(t.mono(M + 64, yy, dd, tamanho=10.5, cor=TEXT))

    return svg(W, altura, "".join(corpo), t, "".join(css),
               titulo="Projeto em destaque: Gemóvel, sistema de gestão de imóveis de temporada (Python, Flask, MySQL, JS), feito em dupla.")


# ================================================================ BOTÕES
def botao(rotulo: str, primario: bool = False, com_seta: bool = True) -> str:
    """Pílula como os botões do site. Escura no contorno, creme na principal (borda preta
    para não sumir no tema claro do GitHub)."""
    t = Textos()
    tam = 16
    largura_txt = medir(rotulo, tam, "SG", 700, -0.02)
    largura = round(largura_txt + 56 + (22 if com_seta else 0))
    altura = 52
    fundo, borda, cor = (TEXT, INK, INK) if primario else (INK, LINE_STRONG, TEXT)
    corpo = [f'<rect x="1" y="1" width="{largura - 2}" height="{altura - 2}" rx="25" fill="{fundo}" stroke="{borda}" stroke-width="1.5"/>',
             t.texto(28, 31.5, rotulo, tamanho=tam, peso=700, cor=cor, espaco_em=-0.02)]
    css = ""
    if com_seta:
        corpo.append(seta(28 + largura_txt + 12, 31, 10, cor, 1.8, classe="seta"))
        css = (".seta{animation:seta 3.6s ease-in-out infinite}"
               "@keyframes seta{0%,72%,100%{transform:translate(0,0)}82%{transform:translate(2.5px,-2.5px)}}")
    return svg(largura, altura, "".join(corpo), t, css, titulo=rotulo, fundo=None)


# ================================================================ CONTATO
def contato() -> str:
    t = Textos()
    css, corpo = [], []
    corpo.append(linha_cabeca(t, 50, "04 / Contato", "Respondo rápido"))
    tam = 58
    linhas = ["Vamos construir", "algo com presença?"]
    t.usar("".join(linhas), "SG", 700)
    trecho, y = palavras(t, linhas, M - 2, 84 + CAP * tam, tam, tam * 0.98, peso=700, espaco_em=-0.05,
                         classe="final", atraso0=0.6, passo=0.11)
    corpo.append(trecho)
    css.append(f".final{{fill:{TEXT};stroke:{VAZADO};stroke-width:1.2;animation:preenche 12s ease-in-out infinite both}}"
               "@keyframes preenche{0%{fill-opacity:0}5%{fill-opacity:1}84%{fill-opacity:1}91%,100%{fill-opacity:0}}")
    par, y = paragrafo(t, "Estou em busca da minha primeira oportunidade. Me chama — respondo rápido.",
                       M, y + 50, 420, 17, 25)
    corpo.append(par)
    y += 52
    corpo.append(t.texto(M, y, "coyotisr@gmail.com", tamanho=26, peso=500, espaco_em=-0.03))
    largura_email = medir("coyotisr@gmail.com", 26, "SG", 500, -0.03)
    corpo.append(f'<line class="sublinha" x1="{M}" y1="{y + 10}" x2="{M + largura_email:.1f}" y2="{y + 10}" stroke="{LINE_STRONG}"/>')
    css.append(f".sublinha{{transform-box:fill-box;transform-origin:left;animation:sublinha 1.2s {EASE_RENDER} 1s both}}"
               "@keyframes sublinha{from{transform:scaleX(0)}}")
    corpo.append(ponto_vivo(W - M - medir("DISPONÍVEL PARA TRABALHO", 12, "JB", 400, 0.06) - 12, y - 4))
    corpo.append(t.mono(W - M, y, "Disponível para trabalho", ancora="end", cor=TEXT_2))
    corpo.append(t.mono(W - M, y - 22, "Hortolândia, SP · UTC−3", ancora="end"))
    altura = round(y + 44)
    return svg(W, altura, "".join(corpo), t, "".join(css),
               titulo="Contato: coyotisr@gmail.com — disponível para trabalho, Hortolândia, SP.")


# ================================================================ RODAPÉ
def rodape() -> str:
    t = Textos()
    css, corpo = [], []
    corpo.append(t.mono(M, 54, "Próxima versão"))
    tam = 44
    frase = "Portfólio completo — em breve"
    t.usar(frase, "SG", 700)
    y = 70 + CAP * tam
    corpo.append(f'<text x="{M - 1}" y="{y:.1f}" font-family="SG" font-weight="700" font-size="{tam}" '
                 f'letter-spacing="{-0.04 * tam:.2f}" fill="none" stroke="{VAZADO}" stroke-width="1.2">{esc(frase)}</text>')
    largura = medir(frase, tam, "SG", 700, -0.04)
    corpo.append(f'<rect class="cursor" x="{M + largura + 8:.1f}" y="{y - CAP * tam:.1f}" width="14" height="{CAP * tam:.1f}" fill="{SIGNAL}"/>')
    css.append(".cursor{animation:pisca 1.06s step-end infinite}@keyframes pisca{0%{opacity:1}50%{opacity:0}}")

    # assinatura: o nome inteiro, atravessado por uma luz (como o rodapé do site)
    nome = "WASHINGTON GABRIEL"
    F = tamanho_para(nome, CONTEUDO)
    y_nome = y + 58 + CAP * F
    t.usar(nome, "SG", 700)
    texto_nome = (f'<text x="{M}" y="{y_nome:.2f}" font-family="SG" font-weight="700" font-size="{F:.2f}" '
                  f'letter-spacing="{-0.05 * F:.2f}">{nome}</text>')
    topo = y_nome - CAP * F
    corpo.append(
        f'<clipPath id="nome">{texto_nome}</clipPath>'
        '<linearGradient id="luz" x1="0" x2="1"><stop offset="0" stop-color="#f6f6f1" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#f6f6f1"/><stop offset="1" stop-color="#f6f6f1" stop-opacity="0"/></linearGradient>'
        f'<g clip-path="url(#nome)" class="animado"><rect x="0" y="{topo - 4:.1f}" width="{W}" height="{CAP * F + 8:.1f}" fill="rgba(246,246,241,.2)"/>'
        f'<g transform="skewX(-22)"><rect class="luz" x="0" y="{topo - 4:.1f}" width="300" height="{CAP * F + 8:.1f}" fill="url(#luz)"/></g></g>'
        f'<g class="estatico" fill="{TEXT}">{texto_nome}</g>'
    )
    css.append(".luz{animation:luz 7s cubic-bezier(0.65,0,0.35,1) 1s infinite both}"
               "@keyframes luz{0%{transform:translateX(-360px)}55%,100%{transform:translateX(1200px)}}")
    y_base = y_nome + 50
    corpo.append(f'<line x1="{M}" y1="{y_base - 24:.1f}" x2="{W - M}" y2="{y_base - 24:.1f}" stroke="{LINE}"/>')
    corpo.append(t.mono(M, y_base, "© 2026 Washington Gabriel"))
    corpo.append(t.mono(W - M, y_base, "Feito à mão com SVG e CSS", ancora="end"))
    return svg(W, round(y_base + 30), "".join(corpo), t, "".join(css),
               titulo="Portfólio completo: em breve. Washington Gabriel.")


def main():
    arquivos = {
        "capa.svg": capa(),
        "projeto.svg": projeto(),
        "contato.svg": contato(),
        "rodape.svg": rodape(),
        "botao-demo.svg": botao("Abrir demo", primario=True),
        "botao-codigo.svg": botao("Ver código"),
        "botao-email.svg": botao("E-mail"),
        "botao-linkedin.svg": botao("LinkedIn"),
        "botao-whatsapp.svg": botao("WhatsApp"),
    }
    for nome, conteudo in arquivos.items():
        caminho = salvar(nome, conteudo)
        print(f"{nome:22} {caminho.stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
