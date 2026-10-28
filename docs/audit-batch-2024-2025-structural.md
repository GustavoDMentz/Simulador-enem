# Lote de auditoria 2024–2025 — triagem estrutural de 193 registros

Fonte: `data/fused/questoes_enem_{2024,2025}_AZUL_D{1,2}.jsonl` e `data/audit/manifest.json`, conferidos por posição.

| Prova | Pendentes | Texto/alternativas preenchidos e sem imagem declarada | Com imagem declarada |
|---|---:|---:|---:|
| 2024 D1 | 1 | 1 (bloqueada por identidade) | 0 |
| 2024 D2 | 64 | 28 | 36 |
| 2025 D1 | 69 | 60 | 9 |
| 2025 D2 | 59 | 27 | 32 |
| **Total** | **193** | **116** | **77** |

**115** registros sem imagem declarada e sem autorização anterior são candidatos à auditoria textual, excluindo a posição 2024 D1 Q04, com conflito de identidade/idioma. **77** exigem auditoria visual dedicada.

Todos os 193 registros possuem campos não vazios de enunciado e alternativas A–E, mas isso **não comprova** integridade semântica, correção de gabarito ou fidelidade ao PDF. A Q50 de 2025 D1 mostra precisamente por que preenchimento estrutural não basta (essa Q50 não integra os 193 fused).

## Ordem de ataque
1. Auditar os 115 candidatos sem imagem declarada contra PDF e gabarito oficiais, começando pelos 28 de 2024 D2.
2. Separar 77 com imagem para inspeção e recuperação dos ativos.
3. Reconstruir 13 posições fora do fused, inclusive Q50 com texto/alternativas incompatíveis e Q138 com opções gráficas ausentes.
4. Autorizar individualmente apenas com evidências e hashes compatíveis com o publicador existente.

**Publicado neste lote: 0.** Nenhum registro existente foi modificado.
