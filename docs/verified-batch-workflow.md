# Fornadas automatizadas com evidências oficiais

O script `scripts/prepare_verified_batch.py` reaproveita as três filas existentes em `data/blue-staging`:
- `blue-candidates.jsonl`
- `official-validation.jsonl`
- `official-answer-evidence.jsonl`

Executa a função conservadora `decide()` do publicador de candidatos, exige as mesmas identidades nas três filas e produz um JSONL por lote, com estados `CANDIDATE`, `REVIEW_TEXT`, `REVIEW_ANSWER`, `REVIEW_IMAGE` ou `HOLD`. A saída não aprova nem publica registros; `CANDIDATE` requer evidência visual quando aplicável e autorização independente no manifesto.

Exemplo do lote textual de 2024 D2:

```bash
python scripts/prepare_verified_batch.py \
  --year 2024 --day 2 \
  --positions 93,97,99,102,105,106,107,108,109,116,117,120,126,129,135,140,143,149,151,156,157,159,160,162,165,171,179,180 \
  --output /tmp/enem-2024-d2-text-batch.jsonl
```

Pré-requisito: filas de evidências geradas pelos scripts existentes, com PDFs oficiais e gabaritos. **Não rodar publicação direta a partir deste JSONL**; a publicação final exige as aprovações vinculadas a conteúdo e hashes verificáveis em `scripts/publish_blue_candidates.py`.

Nenhuma nova questão foi aprovada ou publicada pela inclusão deste script.
