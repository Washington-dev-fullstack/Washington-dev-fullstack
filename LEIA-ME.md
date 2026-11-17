# Perfil do GitHub — como publicar e manter

Esta pasta é o repositório especial **`Washington-dev-fullstack/Washington-dev-fullstack`**: o `README.md` dele aparece no topo do perfil.

## Publicar (primeira vez)

O repositório já existe no GitHub, só com o README padrão ("Hi there 👋"). Para trocar pelo novo:

1. Clone o repositório e copie para dentro dele o conteúdo desta pasta: `README.md`, `assets/`, `ferramentas/`, `.github/` e `docs/`. Este `LEIA-ME.md` também pode ir.
2. Faça commit e push na `main`.
3. Na aba **Actions** do repositório, abra "Contribuições" e clique em **Run workflow**. A partir daí o gráfico se refaz sozinho todo dia às 03:17.
   - Se a Action falhar com erro de permissão: **Settings → Actions → General → Workflow permissions → Read and write**.
   - Opcional: crie um token pessoal (classic, sem escopos) e salve como secret `CONTRIB_TOKEN`. Assim o gráfico também conta as contribuições privadas.

## Mudar textos ou visual

Tudo sai de dois scripts, que usam as mesmas cores e fontes do portfólio (`ferramentas/identidade.py`):

```bash
pip install fonttools brotli pillow
python ferramentas/gerar.py            # capa, projeto, contato, rodapé e botões
python ferramentas/contribuicoes.py    # gráfico (sem token, lê a página pública)
python -m unittest discover -s ferramentas/testes
```

- Para trocar as telas do Gemóvel, substitua os PNGs de `ferramentas/capturas/` (1600 × 1000, com a faixa "Demonstração" no topo) e rode o `gerar.py`.
- **Quando o portfólio for lançado:** troque o rodapé ("Portfólio completo — em breve", vazado) por um botão "Ver portfólio" sólido. Vazado é o que ainda não foi entregue; quando sair, ele fica sólido.

## Regras do sistema

- Vazado = rascunho / futuro. Sólido = entregue. Verde = só o que está ao vivo (disponível, demo no ar, hoje no gráfico, o cursor).
- Animações só com `transform` e `opacity` (e `fill-opacity` no preenchimento das palavras). Sem filtro nem desfoque.
- Com "reduzir movimento" ativado no sistema, cada SVG mostra o estado final, parado.
- Fontes: Space Grotesk e JetBrains Mono (SIL Open Font License), embutidas só com as letras usadas.
