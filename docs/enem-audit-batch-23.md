# ENEM — lote 23: 22 questões com alternativas gráficas

Catálogo: 1283 → **1305** pontuáveis. As 1283 anteriores permanecem byte a byte idênticas. Mesmo método dos lotes 14 a 22 (recorte original; uma ou duas regiões empilhadas), agora para questões cujas alternativas A–E são figuras, gráficos ou fórmulas que a camada de texto não traz como alternativas.

| Prova | Novas |
| --- | ---: |
| 2017 D1 (Q21) | 1 |
| 2017 D2 (Q125, Q127, Q164, Q165, Q167, Q168, Q173) | 7 |
| 2018 D1 (Q56) | 1 |
| 2019 D2 (Q113, Q136, Q165, Q171, Q179) | 5 |
| 2022 D2 (Q96, Q141, Q143) | 3 |
| 2023 D2 (Q163, Q168, Q178) | 3 |
| 2024 D2 (Q112, Q121) | 2 |

- **Conteúdo do registro:** as alternativas recebem o texto de apoio padrão do lote 08 ("Alternativa X: reprodução gráfica oficial.") e o recorte original mostra as figuras. O comando (`enunciado`) é todo o texto da questão antes da primeira letra A–E da sequência (o `texto_base` fica vazio); como a exibição é o recorte (`composition`, comando dentro da imagem), esse texto serve de apoio e de leitura por leitores de tela, e traz rótulos das figuras.
- **Gate novo:** `graphic_content` do construtor só aceita a questão se as cinco letras A–E aparecerem em sequência na mesma coluna (letra sozinha ou com um valor curto). Dos 39 candidatos sem fórmulas, **12 reprovaram** (2017 D2 Q152; 2018 D2 Q159; 2020 D1 Q38, Q57, Q58; 2022 D2 Q95; 2024 D2 Q127, Q161, Q168, Q174; 2025 D2 Q138 e Q169) e ficaram de fora.
- **Fora depois da conferência visual (5):** 2022 D2 Q180 (a segunda "região" é a contracapa, com o logotipo grande do ENEM) e 2025 D2 Q108, Q119, Q127 e Q135 (a região traz o cabeçalho/rodapé "Exame Nacional do Ensino Médio" da página). São regiões de continuação espúrias, e o gate automático não pega.
- **Verificação:** as 27 aprovadas no gate foram vistas em folhas de contato empilhadas; 22 ficaram. Todas recebem a, b, c oficiais (1294 questões com TRI).
- **Ainda fora do grupo B:** as 22 com fórmulas (índices e sobrescritos) e as 5 acima.

```sh
python scripts/build_enem_figure_batch_report.py --batch 23
python scripts/apply_enem_batch_23.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio da camada do PDF (com rótulos de figuras) e descrição da imagem genérica; as alternativas têm só o texto de apoio padrão (o conteúdo real está no recorte); conferência por folha de contato.
