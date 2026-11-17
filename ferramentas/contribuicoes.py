"""Gráfico de contribuições, na identidade "Fios de luz".

Em cima, um fio soma cada semana do último ano, com a luz correndo por ele.
Embaixo, cada dia é um quadrado âmbar (mais aceso = mais contribuições); os
dias parados são um pontinho. A linha e as colunas entram juntas, da esquerda.
Hoje tem o anel âmbar de "ao vivo".

Uso:  python ferramentas/contribuicoes.py --login Washington-dev-fullstack
Com GITHUB_TOKEN (ou CONTRIB_TOKEN) no ambiente, lê a API GraphQL; sem token,
lê a página pública de contribuições. A Action roda isto todo dia.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import urllib.request
from datetime import date, timedelta

from identidade import (
    AMBAR, AMBAR_CLARO, FIO, FIO_FORTE, LARGURA as W, MARGEM as M, TEXTO_2, TEXTO_3, Textos, medir, salvar, svg,
)
from luz import camadas_cometa, caminho, comprimento, cometas

Dia = tuple[date, int]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
NIVEIS = ["", "#5c3d16", "#9c6522", "#e3912f", "#ffc76f"]  # do mais apagado ao mais aceso


# ---------------------------------------------------------------- dados
def buscar_graphql(login: str, token: str) -> list[Dia]:
    consulta = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar"
                "{weeks{contributionDays{date contributionCount}}}}}}")
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": consulta, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "perfil-readme"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as r:
        dados = json.load(r)
    semanas = dados["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return sorted((date.fromisoformat(d["date"]), d["contributionCount"]) for s in semanas for d in s["contributionDays"])


def ler_html(html: str) -> list[Dia]:
    """Lê a página pública (github.com/users/<login>/contributions)."""
    datas ={id_: d for d, id_ in re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?id="([^"]+)"', html)}
    contagens = {}
    for id_, texto in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"(\d+) contributions?", texto.strip())
        contagens[id_] = int(m.group(1)) if m else 0
    return sorted((date.fromisoformat(d), contagens.get(id_, 0)) for id_, d in datas.items())


def buscar_html(login: str) -> list[Dia]:
    pedido = urllib.request.Request(f"https://github.com/users/{login}/contributions",
                                    headers={"User-Agent": "perfil-readme"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return ler_html(r.read().decode("utf-8"))


# ---------------------------------------------------------------- contas
def estatisticas(dias: list[Dia]) -> dict:
    total = sum(c for _, c in dias)
    maior = atual = corrida = 0
    for _, c in dias:
        corrida = corrida + 1 if c else 0
        maior = max(maior, corrida)
    # sequência atual: termina hoje, ou ontem se hoje ainda não teve contribuição
    fim = len(dias) - 1
    if dias and dias[-1][1] == 0:
        fim -= 1
    while fim >= 0 and dias[fim][1] > 0:
        atual += 1
        fim -= 1
    pico = max(dias, key=lambda d: (d[1], d[0])) if dias else (date.today(), 0)
    return {"total": total, "maior": maior, "atual": atual, "pico_data": pico[0], "pico": pico[1]}


def nivel(contagem: int, maximo: int) -> int:
    if contagem <= 0 or maximo <= 0:
        return 0
    return min(4, max(1, math.ceil(contagem / maximo * 4)))


def data_pt(d: date, ano: bool = True) -> str:
    return f"{d.day} {MESES[d.month - 1]}" + (f" {d.year}" if ano else "")


def dias_txt(n: int) -> str:
    return f"{n} dia" if n == 1 else f"{n} dias"


# ---------------------------------------------------------------- desenho
def suave(pontos: list[tuple[float, float]], passo: float = 2.0) -> list[tuple[float, float]]:
    """Curva monótona (Fritsch–Carlson) pelos pontos, amostrada a cada `passo` px em x.
    Monótona: não afunda abaixo de zero entre duas semanas paradas, como um spline comum faria."""
    n = len(pontos)
    if n < 2:
        return list(pontos)
    xs, ys = [p[0] for p in pontos], [p[1] for p in pontos]
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            if a * a + b * b > 9:
                k = 3 / math.hypot(a, b)
                m[i], m[i + 1] = k * a * d[i], k * b * d[i]
    saida = []
    for i in range(n - 1):
        h = xs[i + 1] - xs[i]
        passos = max(1, round(h / passo))
        for j in range(passos):
            t = j / passos
            h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
            saida.append((xs[i] + t * h, h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1]))
    saida.append(pontos[-1])
    return saida


def montar_svg(dias: list[Dia]) -> str:
    t = Textos()
    rnd = random.Random(17)
    css, corpo = [], []
    hoje = dias[-1][0]
    est = estatisticas(dias)
    maximo = max((c for _, c in dias), default=0)

    corpo.append(t.texto(M, 58, "Contribuições no GitHub", tamanho=15, peso=500, cor=TEXTO_3))
    corpo.append(t.texto(W - M, 58, f"Atualizado em {data_pt(hoje)}", tamanho=15, cor=TEXTO_3, ancora="end"))

    # o total grande e as três estatísticas
    total = f"{est['total']}"
    corpo.append(t.texto(M - 3, 132, total, tamanho=66, peso=700))
    x_rotulo = M + medir(total, 66, 700) + 12
    corpo.append(t.texto(x_rotulo, 108, "contribuições", tamanho=18, peso=600))
    corpo.append(t.texto(x_rotulo, 131, "no último ano", tamanho=16, cor=TEXTO_2))
    blocos = [("Maior sequência", dias_txt(est["maior"])), ("Sequência atual", dias_txt(est["atual"])),
              ("Dia mais ativo", f"{data_pt(est['pico_data'], ano=False)} · {est['pico']}" if est["pico"] else "—")]
    for i, (rotulo, valor) in enumerate(blocos):
        x = W - M - (2 - i) * 140 - 126
        corpo.append(t.texto(x, 108, rotulo, tamanho=13, peso=500, cor=TEXTO_3))
        corpo.append(t.texto(x, 131, valor, tamanho=18, peso=600))

    # grade de dias: colunas = semanas (domingo em cima)
    celula, passo = 11, 14
    inicio = dias[0][0] - timedelta(days=(dias[0][0].weekday() + 1) % 7)
    colunas = (hoje - inicio).days // 7 + 1
    x0 = M + 36
    y_fio_topo, y_fio_base = 176, 236   # a linha das semanas
    y0 = 270
    largura_grade = colunas * passo - (passo - celula)

    def pos(d: date) -> tuple[float, float, int]:
        col = (d - inicio).days // 7
        lin = (d.weekday() + 1) % 7
        return x0 + col * passo, y0 + lin * passo, col

    entrada, varredura = 0.5, 2.0   # a linha e as colunas entram juntas, da esquerda

    # ---------- o fio das semanas: a soma de cada semana, numa curva só
    semanas = [0] * colunas
    for d, c in dias:
        semanas[pos(d)[2]] += c
    maior_semana = max(semanas) or 1
    pontos = [(x0 + col * passo + celula / 2, y_fio_base - s / maior_semana * (y_fio_base - y_fio_topo))
              for col, s in enumerate(semanas)]
    curva = suave(pontos)
    linha_d = caminho([curva])
    area_d = linha_d + f"L{curva[-1][0]:.1f} {y_fio_base}L{curva[0][0]:.1f} {y_fio_base}Z"
    lista_c, css_c = cometas([curva], rnd, prefixo="s", periodo=max(2200, comprimento(curva) + 400),
                             cauda=170, cabeca=40)
    corpo.append(
        "<defs>"
        f'<linearGradient id="sob" x1="0" y1="{y_fio_topo}" x2="0" y2="{y_fio_base}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{AMBAR}" stop-opacity=".22"/><stop offset="1" stop-color="{AMBAR}" stop-opacity="0"/>'
        "</linearGradient></defs>"
        f'<line x1="{x0}" y1="{y_fio_base}" x2="{x0 + largura_grade}" y2="{y_fio_base}" stroke="{FIO}"/>'
        f'<path class="area" d="{area_d}" fill="url(#sob)"/>'
        f'<path class="semanas" d="{linha_d}" pathLength="1" fill="none" stroke="{AMBAR}" stroke-width="1.6" '
        'stroke-linejoin="round"/>'
        '<g fill="none" stroke-linecap="round">' + camadas_cometa("s", lista_c, [
            ("cauda", f'stroke="{AMBAR_CLARO}" stroke-opacity=".45" stroke-width="2"'),
            ("cabeca", 'stroke="#fff6e6" stroke-width="2.4"')]) + "</g>"
    )
    css.append(css_c)
    css.append(f".semanas{{stroke-dasharray:1 2;animation:desenha {varredura}s linear {entrada}s both}}"
               "@keyframes desenha{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}"
               f".area{{animation:aparece 1s ease-out {entrada + varredura - 0.4:.2f}s both}}"
               "@keyframes aparece{from{opacity:0}}")
    # o pico da semana mais forte, anotado
    if max(semanas):
        col_pico = max(range(colunas), key=lambda c: (semanas[c], c))
        xp, yp = pontos[col_pico]
        rotulo = f"{semanas[col_pico]} na semana"
        lado = "end" if xp > W / 2 else "start"
        xr = xp - 8 if lado == "end" else xp + 8
        atraso = entrada + col_pico / colunas * varredura
        corpo.append(f'<g class="entra" style="animation-delay:{atraso + 0.2:.2f}s">'
                     f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="3" fill="{AMBAR_CLARO}"/>'
                     f'{t.texto(xr, yp - 7, rotulo, tamanho=12, peso=500, cor=TEXTO_2, ancora=lado)}</g>')
        css.append(".entra{animation:entra .8s cubic-bezier(0.22,1,0.36,1) both}"
                   "@keyframes entra{from{opacity:0;transform:translateY(6px)}}")

    # ---------- meses e dias da semana
    ultimo = -9
    for d, _ in dias:
        x, _, col = pos(d)
        if d.day <= 7 and (d.weekday() + 1) % 7 == 0 and col - ultimo >= 3:
            corpo.append(t.texto(x, y0 - 12, MESES[d.month - 1], tamanho=12, peso=500, cor=TEXTO_3))
            ultimo = col
    for lin, nome in ((1, "seg"), (3, "qua"), (5, "sex")):
        corpo.append(t.texto(M, y0 + lin * passo + 9.5, nome, tamanho=12, peso=500, cor=TEXTO_3))

    # dias parados: um pontinho cada, num caminho só (leve)
    vazios = "".join(f"M{pos(d)[0] + 4:.0f} {pos(d)[1] + 4:.0f}h3v3h-3z" for d, c in dias if not c and d != hoje)
    corpo.append(f'<path id="vazios" d="{vazios}" fill="{FIO_FORTE}"/>')

    # dias com contribuição: acendem coluna por coluna, junto com a linha
    por_coluna: dict[int, list[str]] = {}
    for d, c in dias:
        if c and d != hoje:
            x, y, col = pos(d)
            por_coluna.setdefault(col, []).append(
                f'<rect x="{x}" y="{y}" width="{celula}" height="{celula}" rx="2.5" fill="{NIVEIS[nivel(c, maximo)]}"/>')
    for col, rects in sorted(por_coluna.items()):
        atraso = entrada + col / colunas * varredura
        corpo.append(f'<g class="col" style="animation-delay:{atraso:.3f}s">{"".join(rects)}</g>')
    css.append(".col{animation:col .6s ease-out both}@keyframes col{from{opacity:0}}")

    # hoje: ao vivo, com o anel âmbar
    x, y, _ = pos(hoje)
    c_hoje = dias[-1][1]
    if c_hoje:
        corpo.append(f'<rect id="hoje" x="{x}" y="{y}" width="{celula}" height="{celula}" rx="2.5" fill="{AMBAR_CLARO}"/>')
    else:
        corpo.append(f'<rect id="hoje" x="{x + 0.6}" y="{y + 0.6}" width="{celula - 1.2}" height="{celula - 1.2}" rx="2.2" '
                     f'fill="none" stroke="{AMBAR}" stroke-width="1.2"/>')
    corpo.append(f'<rect class="anel" x="{x}" y="{y}" width="{celula}" height="{celula}" rx="2.5" fill="none" '
                 f'stroke="{AMBAR}" stroke-width="1"/>')

    # legenda
    y_leg = y0 + 7 * passo + 36
    corpo.append(t.texto(M, y_leg, "Cada quadrado é um dia; a linha soma as semanas.", tamanho=13, cor=TEXTO_3))
    xl = W - M - medir("mais", 13, 400)
    corpo.append(t.texto(xl, y_leg, "mais", tamanho=13, cor=TEXTO_3))
    xq = xl - 8 - 5 * passo
    for i in range(5):
        xi = xq + i * passo
        if i == 0:
            corpo.append(f'<rect x="{xi + 4}" y="{y_leg - 6}" width="3" height="3" fill="{FIO_FORTE}"/>')
        else:
            corpo.append(f'<rect x="{xi}" y="{y_leg - 10}" width="{celula}" height="{celula}" rx="2.5" fill="{NIVEIS[i]}"/>')
    corpo.append(t.texto(xq - 8, y_leg, "menos", tamanho=13, cor=TEXTO_3, ancora="end"))

    altura = round(y_leg + 34)
    return svg(W, altura, "".join(corpo), t, "".join(css),
               titulo=f"{est['total']} contribuições no GitHub no último ano; maior sequência de {dias_txt(est['maior'])}.")


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--login", default="Washington-dev-fullstack")
    args.add_argument("--json", help="arquivo com [[\"AAAA-MM-DD\", contagem], ...] (para testes)")
    a = args.parse_args()
    if a.json:
        with open(a.json, encoding="utf-8") as f:
            dias = sorted((date.fromisoformat(d), c) for d, c in json.load(f))
    else:
        token = os.environ.get("CONTRIB_TOKEN") or os.environ.get("GITHUB_TOKEN")
        dias = []
        if token:
            try:
                dias = buscar_graphql(a.login, token)
            except Exception as erro:  # cai para a página pública
                print(f"GraphQL falhou ({erro}); usando a página pública")
        if not dias:
            dias = buscar_html(a.login)
    if not dias:
        raise SystemExit("nenhum dado de contribuição encontrado")
    caminho = salvar("contribuicoes.svg", montar_svg(dias))
    print(f"contribuicoes.svg {caminho.stat().st_size / 1024:.1f} KB · {estatisticas(dias)}")


if __name__ == "__main__":
    main()
