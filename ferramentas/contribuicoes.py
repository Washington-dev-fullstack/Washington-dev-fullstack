"""Gráfico de contribuições no estilo do portfólio.

Cada dia do último ano é um quadrado: todos nascem vazados (rascunho) e os dias
com contribuição "renderizam" sólidos, coluna por coluna, atrás de uma linha
verde. Só o dia de hoje fica verde (ao vivo).

Uso:  python ferramentas/contribuicoes.py --login Washington-dev-fullstack
Com GITHUB_TOKEN (ou CONTRIB_TOKEN) no ambiente, lê a API GraphQL; sem token,
lê a página pública de contribuições. A Action roda isto todo dia.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import urllib.request
from datetime import date, timedelta

from identidade import (
    EASE_RENDER, LARGURA as W, LINE, MARGEM as M, SIGNAL, TEXT, TEXT_2, TEXT_3, Textos, medir, ponto_vivo, salvar, svg,
)

Dia = tuple[date, int]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
OPACIDADE = [0, 0.32, 0.55, 0.78, 1.0]


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
def montar_svg(dias: list[Dia]) -> str:
    t = Textos()
    css, corpo = [], []
    hoje = dias[-1][0]
    est = estatisticas(dias)
    maximo = max((c for _, c in dias), default=0)

    corpo.append(t.mono(M, 50, "03 / Contribuições"))
    corpo.append(t.mono(W - M, 50, f"Atualizado em {data_pt(hoje)}", ancora="end"))

    # o total grande e as três estatísticas
    total = f"{est['total']}"
    corpo.append(t.texto(M - 2, 128, total, tamanho=60, peso=700, espaco_em=-0.05))
    x_rotulo = M + medir(total, 60, "SG", 700, -0.05) + 10
    corpo.append(t.texto(x_rotulo, 106, "contribuições", tamanho=17, peso=500, cor=TEXT))
    corpo.append(t.texto(x_rotulo, 127, "no último ano", tamanho=17, peso=400, cor=TEXT_2))
    blocos = [("Maior sequência", dias_txt(est["maior"])), ("Sequência atual", dias_txt(est["atual"])),
              ("Dia mais ativo", f"{data_pt(est['pico_data'], ano=False)} · {est['pico']}" if est["pico"] else "—")]
    for i, (rotulo, valor) in enumerate(blocos):
        x = W - M - (2 - i) * 132 - 120
        corpo.append(f'<line x1="{x}" y1="86" x2="{x + 120}" y2="86" stroke="{LINE}"/>')
        corpo.append(t.mono(x, 104, rotulo, tamanho=10.5))
        corpo.append(t.texto(x, 128, valor, tamanho=19, peso=500, espaco_em=-0.02))

    # grade de dias: colunas = semanas (domingo em cima)
    celula, passo = 11, 14
    inicio = dias[0][0] - timedelta(days=(dias[0][0].weekday() + 1) % 7)
    colunas = (hoje - inicio).days // 7 + 1
    x0 = M + 32
    y0 = 186
    largura_grade = colunas * passo - (passo - celula)

    def pos(d: date) -> tuple[float, float, int]:
        col = (d - inicio).days // 7
        lin = (d.weekday() + 1) % 7
        return x0 + col * passo, y0 + lin * passo, col

    # meses no topo
    ultimo = -9
    for d, _ in dias:
        x, _, col = pos(d)
        if d.day <= 7 and (d.weekday() + 1) % 7 == 0 and col - ultimo >= 3:
            corpo.append(t.mono(x, y0 - 10, MESES[d.month - 1], tamanho=10))
            ultimo = col
    for lin, nome in ((1, "seg"), (3, "qua"), (5, "sex")):
        corpo.append(t.mono(M, y0 + lin * passo + 9, nome, tamanho=9.5))

    # rascunho: todos os dias vazados num único caminho (leve)
    caminho = "".join(f"M{pos(d)[0] + 0.5:.1f} {pos(d)[1] + 0.5:.1f}h{celula - 1}v{celula - 1}h-{celula - 1}Z"
                      for d, _ in dias if d != hoje)
    corpo.append(f'<path d="{caminho}" fill="none" stroke="rgba(246,246,241,.17)" stroke-width="1"/>')

    # entregue: os dias com contribuição, renderizando coluna por coluna atrás da linha verde
    varredura = 1.8
    por_coluna: dict[int, list[str]] = {}
    for d, c in dias:
        if c and d != hoje:
            x, y, col = pos(d)
            por_coluna.setdefault(col, []).append(
                f'<rect x="{x}" y="{y}" width="{celula}" height="{celula}" fill="{TEXT}" opacity="{OPACIDADE[nivel(c, maximo)]}"/>')
    for col, rects in sorted(por_coluna.items()):
        atraso = 0.4 + col / colunas * varredura
        corpo.append(f'<g class="col" style="animation-delay:{atraso:.3f}s">{"".join(rects)}</g>')
    css.append(f".col{{animation:col .5s {EASE_RENDER} both}}@keyframes col{{from{{opacity:0}}}}")
    corpo.append(f'<line class="varre" x1="{x0 - 4}" y1="{y0 - 4}" x2="{x0 - 4}" y2="{y0 + 7 * passo}" stroke="{SIGNAL}" stroke-width="1.5"/>')
    css.append(f".varre{{opacity:0;animation:varre {varredura}s linear .4s both}}"
               f"@keyframes varre{{0%{{opacity:1;transform:translateX(0)}}90%{{opacity:1}}"
               f"100%{{opacity:0;transform:translateX({largura_grade + 8}px)}}}}")

    # hoje: verde, ao vivo
    x, y, _ = pos(hoje)
    c_hoje = dias[-1][1]
    pintura = f'fill="{SIGNAL}"' if c_hoje else f'fill="none" stroke="{SIGNAL}" stroke-width="1.2"'
    deslocar = 0 if c_hoje else 0.6
    corpo.append(f'<rect class="vivo" x="{x + deslocar}" y="{y + deslocar}" width="{celula - 2 * deslocar}" '
                 f'height="{celula - 2 * deslocar}" {pintura}/>')

    # legenda
    y_leg = y0 + 7 * passo + 34
    corpo.append(f'<line x1="{M}" y1="{y_leg - 20}" x2="{W - M}" y2="{y_leg - 20}" stroke="{LINE}"/>')
    corpo.append(t.mono(M, y_leg, "Vazado = sem commit · sólido = entregue · verde = hoje", tamanho=10))
    xl = W - M - medir("MAIS", 10, "JB", 400, 0.06)
    corpo.append(t.mono(xl, y_leg, "mais", tamanho=10))
    xq = xl - 8 - 5 * passo
    for i in range(5):
        xi = xq + i * passo
        if i == 0:
            corpo.append(f'<rect x="{xi + 0.5}" y="{y_leg - 9.5}" width="{celula - 1}" height="{celula - 1}" fill="none" stroke="rgba(246,246,241,.17)"/>')
        else:
            corpo.append(f'<rect x="{xi}" y="{y_leg - 10}" width="{celula}" height="{celula}" fill="{TEXT}" opacity="{OPACIDADE[i]}"/>')
    corpo.append(t.mono(xq - 8, y_leg, "menos", tamanho=10, ancora="end"))

    altura = round(y_leg + 30)
    return svg(W, altura, "".join(corpo), t, "".join(css),
               titulo=f"{est['total']} contribuições no último ano; maior sequência de {dias_txt(est['maior'])}.")


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
