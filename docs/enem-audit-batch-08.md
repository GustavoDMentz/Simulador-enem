# ENEM — recuperação do lote 08

Base: `235199d913232f4fc706ff311fed3df62fed114a` (PR #9). Branch: `feat/enem-audit-batch-08`.

As 185 pendências foram examinadas individualmente. Foram recuperadas 181 questões; 3 são oficialmente anuladas e 1 mantém conflito de identidade. O catálogo preparado contém **509/513 questões pontuáveis (99,22%)**. As 328 anteriores permanecem byte a byte idênticas. Nenhum banco de produção foi acessado.

## Evidência e decisões

O relatório [batch-08-review.json](../data/audit/batch-08-review.json) registra para cada um dos 185 itens a fonte e o gabarito oficiais, seus SHA-256, aplicação, idioma, número, páginas/retângulos originais, extração auxiliar e decisão. Nas aprovações inclui antes/depois integral, dimensões e hashes dos PNGs, recortes em pixels, verificações visuais e metadados de apresentação. Os hashes do texto extraído auxiliam a reprodução; **não certificam fidelidade visual**. A aprovação é uma decisão explícita após comparação com os pixels oficiais, não uma classificação por OCR, similaridade ou resposta de IA.

### Identidade e aplicação

- `2020_AZUL_D2_Q91`: tomada/adaptador da **aplicação digital**, prova `2020_PV_digital_D2_CD7.pdf`, resposta D. As 36 pendências de 2020/D2 correspondem à aplicação digital; 35 foram recuperadas e Q157 é anulada. A numeração de anulações da aplicação impressa não foi transferida para a digital.
- Treze associações erradas de texto legado foram restauradas na **posição canônica original**, sem renumerar IDs nem alterar `co_item`: 2022/D1 Q07, Q09, Q27; 2024/D1 Q05, Q19; 2024/D2 Q95; 2025/D1 Q17, Q20, Q26, Q30, Q32, Q34, Q37. A linhagem de `scripts/fuse.py` associa os metadados oficiais por prova/posição, enquanto o texto provém da extração. O relatório explicita a reconciliação e preserva o conteúdo anterior; a referência adotada é o caderno oficial na posição original.
- `2024_AZUL_D1_Q04` continua bloqueada. O texto legado está associado à Q05 em inglês, mas seu gabarito histórico C não coincide com Q04 em inglês (A) nem espanhol (D). Não houve confirmação independente de `CO_ITEM`/idioma. As tentativas locais e em CI de recuperar apenas `ITENS_PROVA` dos microdados falharam por transporte/certificados/timeout; nenhum CSV foi obtido, nenhum arquivo de participantes foi lido. A falha não foi tratada como evidência de identidade.

### Anulações oficiais

| Identificador | Aplicação | Decisão |
|---|---|---|
| `2020_AZUL_D2_Q157` | digital | [Gabarito definitivo](https://download.inep.gov.br/enem/provas_e_gabaritos/2020_GB_digital_D2_CD7.pdf) — Anulada |
| `2021_AZUL_D2_Q138` | regular | [Gabarito definitivo](https://download.inep.gov.br/enem/provas_e_gabaritos/2021_GB_impresso_D2_CD7.pdf) — anulada |
| `2022_AZUL_D2_Q157` | regular | [Gabarito definitivo](https://download.inep.gov.br/enem/provas_e_gabaritos/2022_GB_impresso_D2_CD7.pdf) — Anulado |

Não há casos classificados como `SOURCE_UNAVAILABLE` ou `UNRESOLVED`: as provas/gabaritos necessários foram recuperados. A indisponibilidade da tabela auxiliar de itens é uma limitação da investigação de identidade, não ausência das provas.

## Recuperação e apresentação

- As sete pendências gráficas prioritárias (2021 Q102, Q105, Q126, Q135, Q137, Q162 e 2022 Q160) foram conferidas com os originais e recuperadas. Ao todo, 21 questões têm **105 alternativas gráficas** com associação A–E, hash individual e ampliação por teclado.
- 74 novas questões usam HTML para texto verificado; 6 usam figuras independentes e 101 preservam composições com fórmulas, tabelas, documentos ou figuras. A composição de 2019/Q124, a continuidade em 2020 digital/Q123 e Q180, as duas colunas de 2021/Q137 e a tabela integral de Q162 foram corrigidas.
- As figuras são reproduções dos pixels oficiais, sem redesenho. Quando não foi demonstrada uma separação segura, o apoio integral é preservado e ampliável, com o comando e alternativas exibidos separadamente. O original completo também fica disponível para consulta.
- Transcrições de inglês e créditos foram corrigidas pela fonte, incluindo o PDF de 2021 com mapeamento de fonte defeituoso. Poemas mantêm quebras de linha. Expoentes, índices e fórmulas complexas permanecem em imagem quando sua transcrição não seria suficientemente fiel.
- A validação real revelou e corrigiu o fio inferior cortado da alternativa B de 2021/Q126, o apoio vazio de 2019/Q124, o mapa omitido de 2025/Q161, o D inicial de “Das reflexões” em 2024/Q29 e marcadores A–E anexados indevidamente ao texto em extrações de 2022–2023.
- A pontuação passa a exigir também o hash de **todos** os recursos visuais revisados do lote. Uma alternativa gráfica ausente/corrompida bloqueia o item em Python e Node; não há liberação automática de pendências.

## Reprodução

Obtenha os PDFs originais pelos URLs do relatório e salve-os em uma pasta usando `source_file`/`key_file`. Os arquivos são aceitos somente se os SHA-256 corresponderem. Os PDFs permanecem fora do Git; os recortes revisados são versionados.

```sh
python scripts/apply_enem_batch_08.py --pdf-root data/sources/batch08
python scripts/build_question_presentation.py
python scripts/build_question_presentation.py --check
python -m pytest -q tests scripts/tests
node --test web/tests/*.test.js
python scripts/audit_fused_db.py --fused data/fused --output /tmp/db-report.json
```

O replay exige PyMuPDF e Pillow já usados no processamento de imagens. Os PNGs desta revisão foram congelados com PyMuPDF 1.26.6 / Pillow 12.3.0. Outra versão pode produzir antialiasing/PNG diferente e será rejeitada pelo hash; isso exige investigação, não atualização automática do hash. O cache de imagens do MuPDF é esvaziado entre recortes para tornar a reprodução independente da ordem.

Para o navegador, use Playwright e Chromium disponíveis no ambiente, sem adicioná-los às dependências do aplicativo:

```sh
ENEM_CHROMIUM=/caminho/chromium node web/tests/batch08.browser.cjs
ENEM_CHROMIUM=/caminho/chromium node web/tests/rendering.browser.cjs
ENEM_CHROMIUM=/caminho/chromium node web/tests/simulator.browser.cjs
```

## Distribuição das recuperadas

| Ano | LC | CH | CN | MT | Total |
|---|---:|---:|---:|---:|---:|
| 2018 | 3 | 1 | 5 | 4 | 13 |
| 2019 | 5 | 0 | 3 | 0 | 8 |
| 2020 | 5 | 0 | 21 | 14 | 40 |
| 2021 | 5 | 0 | 4 | 2 | 11 |
| 2022 | 9 | 0 | 0 | 1 | 10 |
| 2023 | 5 | 0 | 4 | 10 | 19 |
| 2024 | 38 | 0 | 6 | 6 | 50 |
| 2025 | 12 | 1 | 5 | 12 | 30 |

## Lista completa de decisões

| Identificador | Área | Classificação | Publicação |
|---|---|---|---|
| `2018_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D1_Q90` | CH | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q108` | CN | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q109` | CN | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q116` | CN | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q117` | CN | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q131` | CN | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q139` | MT | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q144` | MT | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q176` | MT | `RECOVERABLE` | Aprovada |
| `2018_AZUL_D2_Q177` | MT | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D1_Q04` | LC | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D2_Q112` | CN | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D2_Q120` | CN | `RECOVERABLE` | Aprovada |
| `2019_AZUL_D2_Q124` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D1_Q04` | LC | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q91` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q93` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q96` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q101` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q102` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q106` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q107` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q111` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q113` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q115` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q118` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q120` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q121` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q123` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q125` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q126` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q127` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q128` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q129` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q131` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q135` | CN | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q138` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q144` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q146` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q147` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q154` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q155` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q156` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q157` | — | `OFFICIALLY_ANNULLED` | Bloqueada |
| `2020_AZUL_D2_Q166` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q169` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q173` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q175` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q176` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q177` | MT | `RECOVERABLE` | Aprovada |
| `2020_AZUL_D2_Q180` | MT | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D1_Q04` | LC | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D2_Q102` | CN | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D2_Q105` | CN | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D2_Q126` | CN | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D2_Q135` | CN | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D2_Q137` | MT | `RECOVERABLE` | Aprovada |
| `2021_AZUL_D2_Q138` | — | `OFFICIALLY_ANNULLED` | Bloqueada |
| `2021_AZUL_D2_Q162` | MT | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q04` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q07` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q09` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q27` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D1_Q33` | LC | `RECOVERABLE` | Aprovada |
| `2022_AZUL_D2_Q157` | — | `OFFICIALLY_ANNULLED` | Bloqueada |
| `2022_AZUL_D2_Q160` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D1_Q04` | LC | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q110` | CN | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q116` | CN | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q121` | CN | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q127` | CN | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q140` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q154` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q156` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q157` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q161` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q165` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q166` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q174` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q176` | MT | `RECOVERABLE` | Aprovada |
| `2023_AZUL_D2_Q177` | MT | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q04` | — | `IDENTITY_CONFLICT` | Bloqueada |
| `2024_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q11` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q12` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q13` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q14` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q15` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q16` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q17` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q19` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q20` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q21` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q22` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q23` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q24` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q25` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q26` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q27` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q28` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q29` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q30` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q31` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q32` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q33` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q34` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q35` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q36` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q37` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q38` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q39` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q40` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q41` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q42` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q43` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q44` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D1_Q45` | LC | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q95` | CN | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q98` | CN | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q113` | CN | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q118` | CN | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q125` | CN | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q130` | CN | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q144` | MT | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q158` | MT | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q163` | MT | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q173` | MT | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q175` | MT | `RECOVERABLE` | Aprovada |
| `2024_AZUL_D2_Q176` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q01` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q02` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q03` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q04` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q05` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q17` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q20` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q26` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q30` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q32` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q34` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q37` | LC | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D1_Q64` | CH | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q96` | CN | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q97` | CN | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q106` | CN | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q107` | CN | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q129` | CN | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q137` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q143` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q144` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q148` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q154` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q156` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q161` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q163` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q165` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q167` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q168` | MT | `RECOVERABLE` | Aprovada |
| `2025_AZUL_D2_Q178` | MT | `RECOVERABLE` | Aprovada |

## Limitações remanescentes

- A questão 2024/D1/Q04 exige metadados oficiais adicionais para resolver a identidade/idioma. Ela não é declarada irrecuperável e continua sem pontuação.
- Anulações não são recuperáveis para pontuação; seus registros históricos são preservados.
- Gráficos/estruturas químicas e outros apoios complexos ainda dependem de visão e ampliação. As descrições dos recortes identificam sua função; não equivalem a uma transcrição matemática completa para leitores de tela. Não foram inventadas descrições numéricas como substituto do original.
- Alguns apoios mistos continuam como composições originais, sobretudo quando texto, fórmulas e rótulos não foram separados com segurança. O modo ampliado mantém todos os dados, mas pode exigir rolagem no celular.
- A tabela `ITENS_PROVA` não foi adquirida: o lote não reivindica revalidação independente dos códigos `CO_ITEM` nem validação de parâmetros TRI.

Os resultados finais dos testes e as capturas de interface acompanham o PR. Nenhum merge foi realizado.


## Verificação final

- 83 testes Python e 13 testes Node/API aprovados.
- Reaplicação completa dos PDFs oficiais concluída: 509 publicadas, 513 na prévia, nenhuma quarentena. Metadados de apresentação conferidos e as 328 anteriores preservadas byte a byte.
- Integridade dos 3.687 registros legados: nenhum problema.
- Os cinco casos de regressão de apresentação passaram em desktop e celular, incluindo teclado, ampliação, retorno de foco e ausência de transbordamento horizontal.
- O teste de navegador seleciona as alternativas pelo teclado: clicar no centro de um cartão gráfico pode atingir seu botão de ampliação e não equivale a escolher a resposta.

- Chromium: 181 novas questões em cada viewport, 724 respostas corretas/incorretas, 424 ampliações, 40 seleções aleatórias; 21 conjuntos de alternativas gráficas em cada viewport. Sem erros JavaScript ou transbordamento horizontal.
- Os quatro bloqueios foram conferidos também na interface de prévia, em ambos os tamanhos. O teste passou a escolher explicitamente uma pendência, pois a primeira questão da prévia foi recuperada neste lote.
- Evidências estruturadas: [batch-08-verification.json](../data/audit/batch-08-verification.json). [12 capturas da amostra](batch08-screenshots) integram a entrega; 52 capturas foram geradas no teste do lote.
- Escopo do navegador: todas as 181 adições e cinco regressões anteriores em cada viewport. A varredura opcional adicional das 509 questões não tem resultado concluído e não é contabilizada nesta verificação.
- Publicação remota autorizada explicitamente pelo responsável em 27/10/2026. O resultado da CI acompanha os checks do PR; este relatório registra as verificações locais. Sem merge automático.
