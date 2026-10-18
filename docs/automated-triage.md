# Triagem automática de qualidade — fase 1

A triagem reduz o trabalho de inspeção manual **sem transformar heurísticas em aprovação**.

```bash
python scripts/triage_questions.py \
  --input data/visual-audit/2024-azul-d1/review/question-review.json \
  --images data/visual-audit/2024-azul-d1/questions \
  --output data/visual-audit/2024-azul-d1/review/triage-report.json
```

O relatório contém, para cada candidato, `checks`, `flags` e `status`.

- `blocked`: hash do PDF inconsistente ou hash do PNG divergente.
- `needs_review`: faltam evidências independentes suficientes para publicação.
- **Nenhum item recebe aprovação automática nesta fase.**

Verificações iniciais: hash da origem, cabeçalho, alternativas A–E, duplicatas e hash do PNG quando fornecido. A presença textual de alternativas não comprova que elas foram extraídas corretamente. O hash de um PNG confirma apenas que o arquivo é o mesmo da extração, não que o recorte está completo.

## Próxima etapa para aprovação automática

1. Ingerir gabarito oficial de forma versionada, com identificação inequívoca de aplicação, caderno e variante de língua.
2. Construir verificações de integridade geométrica e continuidade de página, com tratamento de gráficos vetoriais e textos em duas colunas.
3. Comparar extrações independentes e medir discordâncias.
4. Criar conjunto de validação manual estratificado, incluindo questões com imagens e questões que atravessam páginas.
5. Medir falsos positivos de aprovação automática; só habilitar publicação automática após critérios de qualidade definidos e evidência empírica.

O exportador atual permanece conservador e exige aprovação editorial explícita. A triagem **não altera** `review_status` e não substitui o exportador.
