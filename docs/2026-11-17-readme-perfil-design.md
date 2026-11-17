# README do perfil do GitHub — design "Fios de luz"

**Data:** 2026-11-17 · **Status:** direção escolhida na conversa; versão final aguarda a aprovação do Washington antes do commit.
Substitui a primeira versão, que repetia a identidade do portfólio ("Código → Render").

## Intenção
O perfil é visitado por recrutadores. A primeira versão recriava o portfólio e por isso parecia menos criativa. Esta tem **identidade própria**: o nome é tecido por fios finos, como fibra óptica, e a luz âmbar corre por eles. Enquanto o portfólio não sai, o README leva o recrutador ao **Gemóvel** (GitHub Pages) e ao **contato**.

## Metas
- Abrir com o nome num efeito bonito e vivo, no nível do efeito em canvas do rodapé do portfólio, mas diferente dele.
- Manter o gráfico de contribuições (a parte de que o Washington gostou), redesenhado na identidade nova.
- Animação leve e fluida.

## Anti-metas
- Nada de numeração de seção ("01 / Sobre") nem de etiquetas mono: dão cara de modelo feito por IA.
- Nada de manifesto, pilares numerados ou faixa de tecnologias: blocos de modelo pronto.
- Não repetir o portfólio: nem o preto neutro, nem a Space Grotesk, nem vazado/sólido, nem o corte diagonal, nem os feixes de luz.

## Abordagens consideradas (escolha do Washington: 1)
1. **Fios de luz** — o nome tecido por centenas de fios que seguem um "vento"; pulsos de luz correm pelos fios e acendem ao atravessar as letras. Paleta noite + âmbar/coral.
2. Grade de dias — o nome montado com ~2 mil quadradinhos, como um gráfico de contribuições em alta resolução.
3. Água — o nome fatiado em faixas que ondulam como reflexo; visual editorial claro.

## Sistema
- **Cores:** noite `#0b0c10` (fundo de todo painel, com cantos arredondados), texto creme quente `#f3eee6`, âmbar `#ffb347` e coral `#ff7a45`.
- **Âmbar = luz:** só o que se move ou está ao vivo (pulsos, "disponível", hoje no gráfico, o botão principal).
- **Fonte:** Syne (OFL), embutida só com as letras usadas. O nome em 700: a 800 é larga demais para "WASHINGTON".
- **Fio:** o nome e "Me chama." são tecidos; divisórias e a moldura do Gemóvel são fios por onde a luz passa.

## Peças (em ordem)
1. **Nome:** WASHINGTON / GABRIEL tecidos por fios (linhas de fluxo com espaçamento uniforme, Jobard & Lefer), sobre um vento de fios quase invisíveis. Chegam numa frente ondulada que acende os fios; depois, pulsos com rastro cruzam o painel e acendem dentro das letras. Ao lado de GABRIEL: "Desenvolvedor full stack / em formação, de Hortolândia (SP)" e "● Disponível para trabalho".
2. **Gemóvel:** título, descrição, a tela grande; a Agenda entra tecida, faixa por faixa, com uma "lançadeira" de luz na borda de cada faixa, e sai do mesmo jeito. A luz dá a volta na moldura. Ficha: Ano, Tipo, Stack, Equipe (em dupla com Arthur Gazzoli). Botões "Abrir o Gemóvel" (âmbar) e "Ver o código".
3. **Contribuições:** o total grande, três números (maior sequência, sequência atual, dia mais ativo), um fio que soma cada semana (curva monótona, com a luz correndo) e a grade de dias em quatro tons de âmbar; dia parado é um pontinho.
4. **Contato:** "Tem uma vaga ou uma ideia?" e "Me chama." tecido, e-mail, status. Botões E-mail (âmbar), LinkedIn, WhatsApp.
5. **Rodapé:** "Portfólio completo chegando em breve." sobre o vento ralo. Quando o portfólio sair, vira um botão "Ver portfólio".

## Restrições do GitHub
- README não roda JS nem CSS próprio: a animação mora dentro de SVGs mostrados como `<img>`. Links são SVGs separados dentro de `<a>`.
- Imagens e fontes dentro do SVG só como data URI.
- Animação só com `transform`, `opacity` e `stroke-dashoffset`; recortes sincronizados em SMIL. Sem filtro nem desfoque.
- "Reduzir movimento": cada SVG mostra um quadro parado, com a luz parada no meio dos fios.

## Decisões do construtor
- `fios.py` (numpy + Pillow) gera os fios só no `gerar.py`, rodado à mão. `luz.py` (sem dependências) tem os pulsos e serve também ao gráfico da Action, que continua precisando só do fonttools.
- Todos os pulsos têm o mesmo período (pathLength normalizado), então uma só animação e as mesmas classes servem a todos.
