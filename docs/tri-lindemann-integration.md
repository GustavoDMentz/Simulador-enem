# Fonte TRI: Henrique Lindemann / analise-enem

Fonte externa avaliada: https://github.com/HenriqueLindemann/analise-enem (branch `master`).

## Escopo

O projeto de origem **não é uma base de enunciados**: fornece parâmetros TRI, mapeamento de cadernos, cálculo de notas e métricas de validação para provas de 2009 a 2025. Não usar como fonte de enunciados de 2024/2025.

Licença: **PolyForm Noncommercial 1.0.0**, com aviso obrigatório:

> Required Notice: Copyright (c) 2026 Henrique Lindemann  
> https://github.com/HenriqueLindemann/analise-enem

Licença original: https://github.com/HenriqueLindemann/analise-enem/blob/master/LICENSE

Uso de código ou arquivos derivados requer preservar licença e avisos e respeitar restrições não comerciais. A atribuição, por si só, não libera uso comercial.

## Integração implementada no PR #20 (não mesclada)

- Adotar **adaptador isolado e opcional**; não copiar integralmente o pacote, não alterar a base publicada e não mudar os cálculos correntes sem testes.
- Conferir `src/tri_enem/data/itens` e `mapeamento_provas.yaml` contra a identificação local `ano + co_item`, área, posição/cor/aplicação, idioma e gabarito oficial.
- Separar parâmetros oficiais dos ajustes/reconstruções e escalas estimadas pelo projeto externo; não marcá-los como `VERIFIED` sem cotejo independente.
- Usar a API `SimuladorNota.calcular()` apenas para provas completas compatíveis, exibindo o status de precisão e sinalizando notas estimadas.
- Validar correspondências 2024/2025, anulações, LC inglês/espanhol, duplicatas e regressões; preservar integralmente o catálogo existente.
- Manter proveniência, versão/commit da fonte, licença, e relatório de comparação antes de eventual importação.

**Estado atual:** 2009–2025 em staging externo; 509 itens publicados (2018–2025) associados por ano, CO_ITEM e área; 150 divergências de letra preservadas apenas como diagnóstico. O gabarito do simulador não é sobrescrito. O carregador da API expõe a/b/c e status IDENTITY_MATCHED_EXTERNAL, com prioridade para VERIFIED. A interface exibe os coeficientes e informa quando a fonte externa não foi certificada. Não há cálculo de nota TRI completa nesta integração. O cotejo independente dos coeficientes a/b/c com arquivos originais do Inep permanece pendente; identidade correspondente não equivale à certificação da fonte. A base externa é sujeita à licença PolyForm Noncommercial 1.0.0, cuja compatibilidade com qualquer distribuição deve ser revisada antes de reutilização comercial.
