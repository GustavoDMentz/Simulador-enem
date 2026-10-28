# Cobertura ENEM 2018–2025: inventário inicial

Escopo confirmado: oito edições, de 2018 a 2025. Meta: 8 × 180 = **1.440 posições**. Fonte: `data/audit/manifest.json` da `main`, com 509 registros autorizados; os quatro bloqueados do catálogo de 513 não constam deste manifesto.

| Ano | D1 autorizadas | D2 autorizadas | Total autorizado | Lacunas até 180 |
|---|---:|---:|---:|---:|
| 2018 | 6 | 16 | 22 | 158 |
| 2019 | 11 | 18 | 29 | 151 |
| 2020 | 10 | 81 | 91 | 89 |
| 2021 | 42 | 54 | 96 | 84 |
| 2022 | 13 | 55 | 68 | 112 |
| 2023 | 13 | 36 | 49 | 131 |
| 2024 | 88 | 22 | 110 | 70 |
| 2025 | 20 | 24 | 44 | 136 |
| **Total** | | | **509** | **931** |

## Interpretação

- Existem **509** registros autorizados nesse recorte; a diferença até 1.440 é de **931 posições sem autorização**, não necessariamente ausentes do repositório.
- A diferença nominal entre 1.440 posições e o catálogo de 513 é de 927, mas os dois números não medem a mesma coisa: 513 inclui quatro bloqueados.
- Anulações oficiais devem permanecer não pontuáveis, mesmo quando as posições estiverem documentadas.
- Há aplicações e variantes de caderno/idioma no legado: não mapear outras cores ou aplicações para o caderno azul automaticamente.
- A autorização do item não certifica parâmetros TRI nem sua elegibilidade para EAP.

## Próxima etapa
1. Cruzar cada posição ausente por ano/dia com `data/fused/` e os PDFs/gabaritos oficiais.
2. Classificar material existente, recuperável, anulado ou dependente de fonte/identidade.
3. Recuperar em lotes, sem alterar os 509 registros aprovados, e testar antes de publicar.
