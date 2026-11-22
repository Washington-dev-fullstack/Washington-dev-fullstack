# Perfil do GitHub — como manter

Esta pasta é o clone do repositório especial **`Washington-dev-fullstack/Washington-dev-fullstack`**: o `README.md` dele aparece no topo do perfil. Para publicar uma mudança, faça commit e push na `main`.

A Action "Contribuições" refaz o gráfico sozinha todo dia às 03:17 (e a cada push que mexa em `ferramentas/`). Se ela falhar com erro de permissão: **Settings → Actions → General → Workflow permissions → Read and write**. Opcional: um token pessoal (classic, sem escopos) salvo como secret `CONTRIB_TOKEN` faz o gráfico contar também as contribuições privadas.

## Mudar textos ou visual

Tudo sai de scripts que dividem as mesmas cores e a mesma fonte (`ferramentas/identidade.py`):

```bash
pip install fonttools brotli pillow numpy
python ferramentas/gerar.py            # nome, projeto, contato, rodapé e botões
python ferramentas/gerar.py capa.svg   # só um deles
python ferramentas/contribuicoes.py    # gráfico (sem token, lê a página pública)
python -m unittest discover -s ferramentas/testes
```

- `fios.py` tece os fios (o nome e "Me chama."); `luz.py` faz os pulsos de luz e as divisórias.
- Para trocar as telas do Gemóvel, substitua os PNGs de `ferramentas/capturas/` (1600 × 1000, com a faixa "Demonstração" no topo) e rode o `gerar.py`.
- **Portfólio no ar (nov/2026):** o rodapé avisa e o botão âmbar "Ver portfólio" (`botao-portfolio.svg`) leva a https://washington-dev-fullstack.github.io/. Se o endereço mudar, troque o link no `README.md`.

## Regras do sistema ("Fios de luz")

- Identidade própria do perfil, de propósito diferente do portfólio: fundo noite azulado, Syne, fios e luz âmbar.
- Fio é a forma de tudo: o nome é tecido; divisórias e a moldura da tela são fios.
- Âmbar = luz: só o que se move ou está ao vivo (pulsos, "disponível", hoje no gráfico, o botão principal).
- Sem numeração de seção nem etiquetas em letra mono (dão cara de modelo pronto). Um teste confere.
- Animações só com `transform`, `opacity` e `stroke-dashoffset`. Sem filtro nem desfoque.
- Com "reduzir movimento" ativado no sistema, cada SVG mostra um quadro parado.
- Fonte: Syne (SIL Open Font License, `ferramentas/fontes/LICENSE-syne.txt`), embutida só com as letras usadas.
