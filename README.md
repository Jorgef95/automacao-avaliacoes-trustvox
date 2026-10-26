# Automação de respostas a avaliações (Trustvox)

Automação em Python (pyautogui + OCR) que responde avaliações de **5★** no painel "Avaliações — Produtos" da Trustvox. Lê o comentário com Tesseract, classifica o tipo e envia uma resposta pré-aprovada. Avaliações abaixo de 5★ ficam para tratativa manual.

> Ferramenta de uso interno, compartilhada como referência. Sem garantia de suporte.

## Como funciona

1. Localiza na tela um card com selo **Novo** ou **Lido** (ignora **Respondido**).
2. Abre o card, lê a nota e o comentário por OCR.
3. Nota diferente de 5★ → não responde.
4. 5★ → classifica o comentário, sorteia 1 de 2 textos da categoria, cola e clica em **Responder**.
5. Trata "Carregar mais" e "Buscar agora" quando a lista acaba.

| Categoria | Quando |
|---|---|
| `sem_comentario` | 5★ sem texto |
| `atendimento` | cita atendimento, vendedor, atendente, equipe |
| `ressalva` | "mas", "porém", "poderia melhorar", "faltou"... |
| `detalhado` | mais de 25 palavras |
| `produto` | demais comentários |

## Requisitos

- Windows, Python 3.9+
- [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) com o idioma **Portuguese** (`por.traineddata`)
- Bibliotecas: instaladas automaticamente na primeira execução (opencv-python, pillow, numpy, pyautogui, pyperclip, keyboard, pytesseract)

Se o `tesseract.exe` não estiver em um local padrão, defina a variável de ambiente `TESSERACT_CMD` com o caminho completo.

## Imagens de referência (você cria)

Salve na **mesma pasta do script**, como PNG, recortando justo da sua tela (mesma resolução e zoom da execução):

`placeholder_resposta.png`, `botao_responder.png`, `carregar_mais.png`, `badge_novo.png`, `badge_lido.png`, `buscar_agora.png`, `nota_5.png`, `sem_comentario.png`, `fechar.png`

## Uso

```
python automacao_respostas.py
```

- `1` Calibrar: mostra coordenadas do mouse (ajuste `X3, Y3` no script).
- `2` Iniciar: informe quantas avaliações processar (comece com 5 a 10).

Não use mouse/teclado durante a execução. Para parar: **ESC**, ou mouse no canto da tela (fail-safe: pausa e pede ENTER).

## Ajustes

Parâmetros no topo do script (`CONFIDENCE`, `SCROLL_POR_AVANCO`, margens do OCR, `LIMITE_DETALHADO_PALAVRAS`) e textos no dicionário `RESPOSTAS`. Os textos incluídos são exemplos genéricos: substitua pelos aprovados na sua empresa.

## Limitações

- Depende de resolução, zoom e layout do painel.
- Classificação por palavras-chave (aproximada).
- Fluxo de avaliações abaixo de 5★ ainda pouco testado.
- Use por sua conta e risco; confira o resultado por amostragem.
