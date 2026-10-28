# Plano operacional — 2024–2025, recuperação sem aprovação automática

## Constatação na árvore da main
- Há quatro arquivos fused azuis de 2024–2025; não foram encontrados arquivos fused de outras cores desses anos na árvore inspecionada.
- O pipeline existente inclui extração de PDFs oficiais, auditoria e publicação com hashes de evidência.
- 13 posições não constam dos arquivos fused azuis: 2024 D1 18; D2 94, 96, 100, 101; 2025 D1 50; D2 138, 151, 152, 153, 157, 158, 159.
- Outras 193 posições estão nos fused, mas não no conjunto autorizado; nenhuma delas deve ser aprovada apenas pela presença no JSONL.

## Ordem de execução
1. Para cada posição ausente, recuperar o recorte do PDF oficial da mesma edição, aplicação, cor e dia; preservar referência, página e hash.
2. Conferir enunciado, cinco alternativas, material visual e gabarito oficial. Bloquear posições ambíguas e anuladas.
3. Para as 193 posições existentes, priorizar revisão de texto/gabarito e deixar questões com imagem complexa em fila específica.
4. Produzir manifesto de evidências compatível com `scripts/publish_blue_candidates.py`, preservando os 509 registros autorizados.
5. Executar testes e publicar somente registros com autorização explícita.

## Observação
Esta triagem não importou questões novas e não certifica os 193 registros pendentes.
