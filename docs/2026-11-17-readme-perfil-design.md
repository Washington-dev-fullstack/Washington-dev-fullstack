# README do perfil do GitHub — design

**Data:** 2026-11-17 · **Status:** aprovado na conversa

## Intenção
O perfil do GitHub (Washington-dev-fullstack) é visitado por recrutadores. Ele deve parecer uma extensão do portfólio "Código → Render": mesmo preto, mesma tipografia, mesmas regras (vazado = rascunho/futuro, sólido = entregue, verde = ao vivo). Enquanto o portfólio não é lançado, o README leva o recrutador ao **Gemóvel** (GitHub Pages) e ao **contato**.

## Metas
- Visual, imersivo e animado, no nível de acabamento do portfólio.
- Animações leves e o mais fluidas possível: só `transform` e `opacity`, sem filtros/desfoque.
- Gráfico de contribuições próprio, no estilo do portfólio.

## Não-metas / anti-metas
- Nada de widgets genéricos de terceiros (stats cards, cobrinha, badges coloridos).
- Nada que dependa de servidor externo para aparecer.
- Nada de efeito "papel de parede" atrás do texto: o efeito nasce das letras.

## Restrições do GitHub
- README não aceita JS nem CSS: a animação mora dentro de SVGs (CSS dentro do SVG), mostrados como imagem.
- Fontes embutidas em base64 no SVG, só com os glifos usados (subconjunto).
- Clique não funciona dentro do SVG: links são SVGs separados envolvidos por `<a>`.
- Imagens dentro de SVG só funcionam como data URI.

## Abordagens do gráfico
1. Serviço de terceiros: zero setup, cara genérica, cai com frequência.
2. Cobrinha (snk): clichê.
3. **Escolhida:** Action diária no repositório do perfil que consulta a API GraphQL e gera `assets/contribuicoes.svg` no estilo do portfólio (dia sem contribuição vazado, com contribuição sólido, hoje verde).

## Estrutura do README (em ordem)
1. Hero: W digitado barra a barra + cursor verde; WASHINGTON vazado que preenche; GABRIEL sólido; anotações mono (Portfólio / 2026, ● Disponível, Hortolândia, SP).
2. Manifesto preenchendo palavra por palavra.
3. Faixa creme com as tecnologias correndo.
4. Projeto 01 / Gemóvel: print que renderiza do rascunho à tela real; ficha (2026, em dupla com Arthur Gazzoli, stack); botões Abrir demo ↗ e Código.
5. Contribuições (gerado pela Action).
6. Contato: "Vamos construir algo com presença?" + E-mail, LinkedIn, WhatsApp.
7. "Portfólio completo: em breve" (vazado).
8. Assinatura: WASHINGTON GABRIEL com luz atravessando as letras.

Texto em PT-BR com uma linha curta em inglês. `prefers-reduced-motion` dentro de cada SVG deixa tudo sólido e parado.

## Decisões do construtor
- Gerador em Python (sem dependências além de fontTools) que monta todos os SVGs a partir de um único script; assim a identidade fica centralizada.
- Arquivos em `Desktop/github-perfil/`, pronto para virar o repositório `Washington-dev-fullstack`. Publicação fica com o Washington.
