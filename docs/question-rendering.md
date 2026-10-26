# Renderização das questões publicadas

Base: `4fa28cd536ab9c3a4281f5b4eb964e5aa8bab6d0` (PR #6). Catálogo: **238 questões**, sem mudanças nos registros, gabaritos, proveniência ou estados de auditoria.

## Diagnóstico

`contem_imagem` indica a existência de um arquivo, não a necessidade pedagógica de uma figura. Os lotes anteriores preservaram recortes de prosa e painéis completos como evidência. O frontend apresentava tanto a transcrição quanto esses recortes indiscriminadamente. O limite de 280 px de altura tornava diagramas e painéis inteiros pequenos. As quebras de linha do PDF também prejudicavam a leitura do HTML.

A solução mantém os originais e acrescenta um manifesto exclusivamente de apresentação, separado da autorização de pontuação. A migração usa as transcrições já verificadas nos relatórios dos lotes 03–05, conferindo conteúdo e hashes. Não usa OCR, classificação automática por presença de texto ou descrições de IA como evidência.

## Política de apresentação

- **78 textos:** HTML com recomposição das quebras simples, preservando parágrafos e listas. O recorte original continua disponível por botão.
- **1 figura complementar:** Q155 apresenta prosa e dados exatos em HTML, intercalados com um recorte independente do diagrama.
- **15 composições:** preservam o painel integral. Nos 14 painéis de fórmulas explicitamente documentados como incluindo o comando, esse comando não é repetido visualmente em HTML.
- **Demais casos:** preservam os recursos originais. Ausência, divergência de hash ou metadados inválidos resulta na apresentação conservadora, nunca na retirada da questão ou liberação de pontuação.

O simulador oferece diálogo nativo com foco inicial, Escape, retorno do foco, ajuste à janela, tamanho original e link para o PNG. A prévia usa a mesma classificação e links para os originais. Imagens preservam proporções; figuras, painéis e texto têm dimensões próprias. Alternativas têm foco visível, seleção por teclado e estados de correção identificados por texto e cor.

## Casos conferidos visualmente

| Caso | Antes | Depois |
| --- | --- | --- |
| `2024_AZUL_D2_Q137` | Prosa em HTML e recorte repetido | Uma apresentação em HTML; original consultável |
| `2024_AZUL_D2_Q155` | Painel completo reduzido | Diagrama independente, prosa e cinco pares α/R legíveis |
| `2018_AZUL_D1_Q74` | Cartilha limitada a 280 px | Composição histórica preservada e ampliável |
| `2018_AZUL_D2_Q110` — código genético | Texto repetido em imagem | Texto acessível sem duplicação |
| `2024_AZUL_D2_Q111` — exoesqueleto | Texto repetido em imagem | Texto acessível sem duplicação |

O identificador solicitado `2018_AZUL_D1_Q076` não está no catálogo publicado. A cartilha está em `2018_AZUL_D1_Q74`; nenhum identificador foi renomeado.

As 15 capturas em [rendering-screenshots](rendering-screenshots/) mostram antes/depois em desktop e depois em celular. São capturas reais de Chromium, com o contêiner de rolagem expandido apenas para registrar o cartão inteiro.

## Migração reproduzível e integridade

```sh
# Regeneração do PNG derivado e manifesto (Pillow necessário apenas aqui)
python scripts/build_question_presentation.py
# Verificação sem Pillow
python scripts/build_question_presentation.py --check
python -m pytest -q tests scripts/tests
node --test web/tests/*.test.js
python scripts/audit_fused_db.py --fused data/fused --output /tmp/enem-integrity.json
```

O recorte de Q155 é `[40, 235, 620, 585]`, em pixels do PNG original `batch05-2024-azul-d2-q155.png`, sem redimensionamento. As transcrições foram comparadas ao painel integral já auditado. O manifesto registra os hashes SHA-256 dos registros, originais e figura derivada; o módulo Node os verifica antes de aplicar a apresentação. Os documentos oficiais e as evidências continuam referenciados nos manifestos anteriores. Não houve nova auditoria nem alteração no mecanismo de pontuação.

SHA-256 do catálogo publicado, antes e depois: `8351f7ef5c3508e9bc1277d7ad8fb6bd6d82113b897fd31db1c621dfdcc906d3`.

## Verificação e limites

O teste `web/tests/rendering.browser.cjs` verifica os cinco casos em 1280×1000 e 390×844: ausência das duplicações conhecidas, preservação da cartilha/figura, valores exatos, dimensões, ampliação, Escape, foco, resposta por teclado e ausência de transbordamento horizontal. `web/tests/simulator.browser.cjs` cobre o catálogo inteiro, respostas corretas/incorretas e seleção aleatória. O servidor funciona com os arquivos auditados sem ArangoDB.

A resolução original é a do PNG preservado; não se promete resolução superior à fonte disponível. Painéis ainda não classificados conservam seu conteúdo integral e ampliação; não se tentou separar automaticamente fórmulas, charges ou documentos históricos. A cartilha continua sendo uma composição visual, com descrição contextual e acesso ao original, não uma transcrição integral acessível. A conferência desta missão reutilizou os recortes e evidências já versionados; os PDFs originais não foram recuperados novamente. A integração ArangoDB é executada pelo workflow existente em banco efêmero de CI, sem acesso à produção.
