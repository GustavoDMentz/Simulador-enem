# Triagem prioritária — ENEM azul 2024 e 2025

Cruzamento por posição entre `data/audit/manifest.json` (509 autorizadas) e `data/fused/questoes_enem_{ano}_AZUL_D{dia}.jsonl` da main. Não é auditoria de conteúdo nem autorização de publicação.

| Prova | Autorizadas | Extraídas no fused | Extraídas não autorizadas | Ausentes do fused |
|---|---:|---:|---:|---:|
| 2024 D1 | 88 | 89 | 1 | 1 |
| 2024 D2 | 22 | 86 | 64 | 4 |
| 2025 D1 | 20 | 89 | 69 | 1 |
| 2025 D2 | 24 | 83 | 59 | 7 |

## Posições ausentes dos arquivos azuis

- 2024 D1: 18
- 2024 D2: 94, 96, 100, 101
- 2025 D1: 50
- 2025 D2: 138, 151, 152, 153, 157, 158, 159

## Fila de revisão (presentes, mas não autorizadas)

- 2024 D1 (1): 4
- 2024 D2 (64): 91, 92, 93, 97, 99, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 114, 115, 116, 117, 119, 120, 121, 122, 123, 124, 126, 127, 128, 129, 131, 132, 134, 135, 136, 138, 139, 140, 142, 143, 147, 148, 149, 150, 151, 152, 154, 156, 157, 159, 160, 161, 162, 164, 165, 167, 168, 169, 171, 172, 174, 177, 178, 179, 180
- 2025 D1 (69): 6, 7, 8, 9, 10, 11, 12, 13, 16, 18, 19, 22, 23, 24, 25, 27, 28, 29, 35, 36, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 88, 89, 90
- 2025 D2 (59): 91, 92, 93, 94, 95, 98, 99, 101, 102, 103, 104, 105, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 130, 131, 132, 133, 134, 135, 136, 139, 140, 141, 142, 145, 147, 149, 150, 155, 160, 164, 166, 169, 170, 171, 172, 173, 174, 177, 180

## Cuidados
- `2024_AZUL_D1_Q04` tem conflito de identidade/idioma documentado no lote 08; não autorizar sem evidência independente.
- Não mapear outra cor nem outra aplicação automaticamente; comparar posição, identidade e gabarito oficiais.
- A lista indica presença estrutural, não fidelidade visual, correção de gabarito ou TRI.
- Preservar os 509 itens autorizados; liberar novas questões apenas após auditoria e testes.
