# ENEM — lote 14: 63 questões com figura de 2017

Catálogo: 936 → **999** pontuáveis. As 936 anteriores permanecem byte a byte idênticas. É o primeiro lote da fase de figuras (grupo A: região única, figura, cinco alternativas em texto).

| Prova | Novas |
| --- | ---: |
| 2017 D1 | 25 |
| 2017 D2 | 38 |

## Método
- **Exibição:** o aluno vê o recorte original do PDF da questão inteira (apresentação `composition`, com comando e alternativas na imagem); o texto da camada do PDF fica como apoio e inclui rótulos das figuras.
- **Caixa do recorte:** união de texto, imagens e desenhos da região, sem a barra do cabeçalho e sem as marcas escuras da margem da página, estendida na vertical até conter por inteiro as linhas que a borda cortaria.
- **Gates automáticos por questão** (`scripts/build_enem_figure_batch_report.py`): nenhuma linha de texto cortada pela borda, nenhum cabeçalho de outra questão dentro do recorte, resposta do `ITENS_PROVA` = gabarito do PDF. Um gate pegou o corte de 2 pt da última linha da Q34 de 2017 D1, corrigido pela extensão da caixa.
- **Conferência visual:** 63 recortes em 11 folhas de contato, mais folha dos recortes finais com as correções.
- Identidade, gabarito e TRI como nos lotes anteriores; o `parametros_tri` do registro é `null` e o carregador junta o TRI oficial pelo `CO_ITEM` resolvido (as 63 recebem a, b, c).
- A seleção fica em `data/audit/figure-batches/batch-14-selection.json`.

```sh
python scripts/build_enem_figure_batch_report.py --batch 14
python scripts/apply_enem_batch_14.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
O texto de apoio vem da camada de texto e traz rótulos das figuras (por isso aparecem `possivel_poesia` e `numeracao_de_linhas` nas flags); a descrição da imagem é genérica. A conferência é por folha de contato, não pixel a pixel.
