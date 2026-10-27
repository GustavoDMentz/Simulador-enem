# ENEM — Auditoria do lote 07

Base: `868754bb38b0ab64a4bdf53befa57c7c989342ad`, após PR #8. Branch: `feat/enem-audit-batch-07`.

## Resultado e escopo

50 questões classificadas individualmente: **40 aprovadas** e **10 mantidas bloqueadas**. O catálogo proposto passa de **288 para 328 publicadas**, com **185 pendentes** no inventário original de 513. As 288 anteriores, incluindo gabaritos e demais campos, foram preservadas byte a byte.

A seleção priorizou exclusivamente Natureza e Matemática. Foram examinadas as 28 pendentes do segundo dia de 2021, as 21 de 2022 e o conflito de identidade de 2020/Q91. Não houve cotas por área nem substituição silenciosa de questões.

| Ano | Examinadas | Aprovadas | Natureza | Matemática | Mantidas em revisão |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 1 | 0 | 0 | 0 | 1 |
| 2021 | 28 | 21 | 13 | 8 | 7 |
| 2022 | 21 | 19 | 13 | 6 | 2 |
| Total | 50 | 40 | 26 | 14 | 10 |

## Novos identificadores

| Identificador | Área | Apresentação |
| --- | --- | --- |
| `2021_AZUL_D2_Q91` | CN | figure |
| `2021_AZUL_D2_Q92` | CN | composition |
| `2021_AZUL_D2_Q93` | CN | figure |
| `2021_AZUL_D2_Q99` | CN | figure |
| `2021_AZUL_D2_Q101` | CN | figure |
| `2021_AZUL_D2_Q103` | CN | figure |
| `2021_AZUL_D2_Q106` | CN | figure |
| `2021_AZUL_D2_Q107` | CN | figure |
| `2021_AZUL_D2_Q109` | CN | figure |
| `2021_AZUL_D2_Q122` | CN | figure |
| `2021_AZUL_D2_Q124` | CN | figure |
| `2021_AZUL_D2_Q125` | CN | figure |
| `2021_AZUL_D2_Q133` | CN | composition |
| `2021_AZUL_D2_Q136` | MT | figure |
| `2021_AZUL_D2_Q140` | MT | composition |
| `2021_AZUL_D2_Q148` | MT | figure |
| `2021_AZUL_D2_Q149` | MT | figure |
| `2021_AZUL_D2_Q150` | MT | figure |
| `2021_AZUL_D2_Q151` | MT | figure |
| `2021_AZUL_D2_Q168` | MT | figure |
| `2021_AZUL_D2_Q169` | MT | figure |
| `2022_AZUL_D2_Q94` | CN | figure |
| `2022_AZUL_D2_Q101` | CN | figure |
| `2022_AZUL_D2_Q107` | CN | figure |
| `2022_AZUL_D2_Q111` | CN | composition |
| `2022_AZUL_D2_Q117` | CN | figure |
| `2022_AZUL_D2_Q118` | CN | figure |
| `2022_AZUL_D2_Q120` | CN | figure |
| `2022_AZUL_D2_Q121` | CN | figure |
| `2022_AZUL_D2_Q125` | CN | figure |
| `2022_AZUL_D2_Q128` | CN | figure |
| `2022_AZUL_D2_Q129` | CN | figure |
| `2022_AZUL_D2_Q134` | CN | composition |
| `2022_AZUL_D2_Q135` | CN | figure |
| `2022_AZUL_D2_Q138` | MT | figure |
| `2022_AZUL_D2_Q149` | MT | figure |
| `2022_AZUL_D2_Q161` | MT | figure |
| `2022_AZUL_D2_Q162` | MT | figure |
| `2022_AZUL_D2_Q176` | MT | figure |
| `2022_AZUL_D2_Q179` | MT | figure |

## Pendências explícitas

- **Anuladas oficialmente:** `2021_AZUL_D2_Q138` e `2022_AZUL_D2_Q157`.
- **Alternativas gráficas sem representação independente concluída:** `2021_AZUL_D2_Q102`, `Q105`, `Q126`, `Q135`, `Q137`, `Q162` (mesmo prefixo) e `2022_AZUL_D2_Q160`. Permanecem sem autorização de publicação.
- **Identidade conflitante:** `2020_AZUL_D2_Q91`. O inventário descreve um adaptador de tomada; a questão 91 da prova regular azul oficial recuperada é uma tirinha do Garfield sobre eletricidade estática. O item não foi substituído por uma pergunta diferente nem renumerado.

## Fontes oficiais e comparação

Aplicação regular, segundo dia, caderno azul 7. Os arquivos foram recuperados pelo host do Inep via HTTP (incluindo `?download=1` no gabarito de 2021 após erros 503). Seus hashes coincidem com as fontes já registradas nos lotes anteriores.

- **2021 — [prova](https://download.inep.gov.br/enem/provas_e_gabaritos/2021_PV_impresso_D2_CD7.pdf)**, SHA-256 `887b2a10ebb163f0c40db2ab4f67a5a4b5959ceb74ce7273466a755b8e55f540`; [gabarito](https://download.inep.gov.br/enem/provas_e_gabaritos/2021_GB_impresso_D2_CD7.pdf), SHA-256 `c78b77767c239fb93350f502f2f9f83bcadc7ae467d77b0a6cd887de8b5f4cc7`.
- **2022 — [prova](https://download.inep.gov.br/enem/provas_e_gabaritos/2022_PV_impresso_D2_CD7.pdf)**, SHA-256 `ab4cdea89504ab1bfc9435addacea482417cd82e9f220abaa6a317a10bd0b0f9`; [gabarito](https://download.inep.gov.br/enem/provas_e_gabaritos/2022_GB_impresso_D2_CD7.pdf), SHA-256 `1b4b0cd0978bfc6c862d9631c4f8a5c25091938d09acfd2bd8c8b510764cb118`.

A fonte do conflito de 2020 é [a prova regular azul](https://download.inep.gov.br/enem/provas_e_gabaritos/2020_PV_impresso_D2_CD7.pdf), SHA-256 `f9970a82e0ee67a31ec16e2f14c99e620738b88dfe7c68484128964a5d5d69bc`, página 2.

As regiões completas e as páginas adjacentes/colunas necessárias foram conferidas visualmente contra os documentos oficiais. O gabarito impresso foi inspecionado e conferido pelo parser existente. Cada decisão registra antes/depois, página, coordenadas, hash do texto bruto extraído, hash do registro e hash dos PNGs. O texto bruto é diagnóstico, não prova automática de fidelidade.

### Camada textual de 2021

O PDF de 2021 contém aliases de fonte com Unicode quebrado. A recuperação auxiliar identificou 113 aliases por programas CFF idênticos a glifos nomeados da própria fonte; hashes e correspondências estão em `data/audit/batch-07-font-recovery.json`. Essa correspondência não foi usada como autorização automática. Prosa, comandos e A–E foram comparados à renderização original. Ligaduras, percentuais e símbolos matemáticos residuais foram transcritos mediante essa conferência visual. A reprodução da publicação não requer FontTools nem OCR.

## Correções e apresentação

35 questões apresentam prosa em HTML e figura/tabela/equação independente. Cinco preservam composições com elementos intercalados ou continuidade entre colunas: 2021/Q92, Q133, Q140 e 2022/Q111, Q134. Nenhum apoio original foi removido por conter texto.

Os recortes preservam os pixels oficiais, incluindo créditos, traçados, escalas e unidades. O comando e A–E ficam fora da imagem, sem duplicação. A ampliação e o tamanho original usam a interface já existente. Um pequeno ajuste aceita legenda posterior vazia em figuras verificadas; metadados ausentes ou inválidos continuam usando a apresentação conservadora, sem afetar a pontuação.

Casos de precisão conferidos incluem:

- 2021/Q91: espécies químicas e concentrações da tabela; H₃PO₄, CaSO₄, Al₂O₃ e FeCl₂ em A–E.
- 2021/Q92 e Q109: índices e todos os sinais `<`, `=` e `>`; nenhuma relação foi inferida pela resolução da questão.
- 2021/Q101: C₆H₁₂O₆, reação original, 80%, 0,80 g/mL e os valores de massa.
- 2021/Q124 e Q133: semirreações, cargas, potenciais e unidades preservados como pixels originais.
- 2021/Q136 e Q169: φ², φ⁷ e √3, sem converter fórmulas em descrições genéricas.
- 2022/Q101, Q107, Q117, Q120 e Q129: mg L⁻¹, H⁺, CaCO₃, H₂O₂ e espécies iônicas com índices/cargas exatos.
- 2022/Q161: dimensões 16 cm, 18,4 cm, 5 cm, 4 cm e escala 1 : 50. A inspeção dos pixels corrigiu um recorte inicial que cortava a borda inferior das legendas.
- 2021/Q122: preservado o esquema inteiro de tratamento de esgoto, incluindo setas e seis etapas; um recorte inicial incorreto foi detectado e corrigido antes da publicação.

Marcas invisíveis de extração `ENEM 2022` e rótulos duplicados de alternativas da camada PDF não foram levados ao HTML. Hifens de quebra de linha foram normalizados. Diferenças completas e exceções matemáticas estão em `data/audit/batch-07-review.json`.

## Reprodução e integridade

Obtenha os PDFs oficiais com os hashes acima em um diretório, nomeados `2021-d2.pdf`, `2021-key.pdf`, `2022-d2.pdf` e `2022-key.pdf`.

```sh
python scripts/apply_enem_batch_07.py --pdf-root data/sources/batch07
python scripts/build_question_presentation.py
python scripts/publish_blue_candidates.py
python scripts/build_question_presentation.py --check
python -m pytest -q tests scripts/tests
node --test web/tests/*.test.js
python scripts/audit_fused_db.py --fused data/fused --output /tmp/b07-integrity.json
```

O aplicador reproduz decisões fixas, exige as fontes de hash exato, confere o gabarito e o vínculo com as regiões originais, reconstitui os PNGs e usa o publicador existente. Não é um algoritmo de aprovação. A reaplicação foi verificada como idempotente. Snapshot de recuperação, registros fused e banco não foram alterados; TRI continua nula.

## Verificação e limites

Os testes protegem a preservação byte a byte das 288 anteriores, os 40 vínculos novos e a exclusão das 185 pendentes. Os testes Chromium percorrem as novas questões em desktop/celular e repetem os cinco casos de regressão do PR #7. A imagem é inspecionada visualmente: sua mera existência não constitui validação.

[Capturas da amostra](batch07-screenshots/) incluem tabelas químicas, fórmulas, relações entre frequências e geometria. As composições densas exigem ampliação em celular; não se promete transcrição acessível integral de estruturas químicas, gráficos ou tabelas. Descrições contextualizam os apoios, sem substituir dados exatos.

O anexo `enem-parte-00` estava indisponível e não foi utilizado. Nenhuma ação de produção ou merge faz parte desta entrega.


Resultados finais: **78 testes Python**, **10 Node/API**, integridade dos **3.687 registros** sem problemas e reaplicação idempotente. Chromium percorreu **40 novas questões em cada viewport**, com **160 respostas corrigidas**, **20 seleções aleatórias** e bloqueio das **185 pendentes**. Os cinco casos do PR #7 passaram em desktop/celular; sem erros JavaScript ou transbordamento horizontal. Em seis verificações adicionais, a largura renderizada em resolução original foi igual à largura natural do PNG; a tabela química também foi percorrida por teclado. Foram registradas 26 capturas da amostra, incluindo ampliação.

O teste de teclado identificou um evento tardio de fechamento do diálogo que podia roubar o foco de uma alternativa. O tratamento de foco foi limitado aos casos em que o foco ainda está no diálogo ou no corpo da página. A regressão reproduz o evento tardio depois de focar a alternativa e confirma a seleção por teclado. Nenhuma questão anterior foi alterada para corrigir esse comportamento.

A conferência final também restaurou os colchetes do crédito `[on-line]` em 2021/Q106 e dos intervalos `]300, 400]` etc. em 2021/Q151. A fonte codificava esses glifos como ¢/£; os símbolos impressos, sem interpretação estatística inferida, prevaleceram. Testes específicos protegem esses casos e C₆H₁₂O₆.
