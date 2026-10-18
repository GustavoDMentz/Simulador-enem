# Gabaritos oficiais — cruzamento por identidade

O script `scripts/reconcile_answer_key.py` **não baixa, autentica ou inventa gabaritos**. Recebe um manifesto de respostas transcrito de fonte verificável, e cruza com `question-review.json` sem alterar os dados originais.

## Formato do manifesto

O exemplo abaixo é **sintético**; URL e respostas não representam o INEP.

```json
{
  "exam": {"year": 2024, "application": "regular", "day": 1, "color": "azul"},
  "source": {
    "url": "https://example.org/documento.pdf",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "verification_status": "pending"
  },
  "answers": [
    {"number": 1, "language_variant": "ingles", "answer": "B"},
    {"number": 1, "language_variant": "espanhol", "answer": "C"},
    {"number": 6, "language_variant": null, "answer": "D"}
  ]
}
```

`verification_status: verified` só deve ser atribuído após verificação externa do documento original e do seu SHA-256. O script **confia nessa declaração** e não autentica a fonte sozinho. Cada caderno requer manifesto próprio. Questões anuladas usam `"ANULADA"` e não são liberadas.

## Execução

```bash
python scripts/reconcile_answer_key.py \
  --review data/visual-audit/2024-azul-d1/review/question-review.json \
  --key data/answer-keys/2024-regular-d1-azul.json \
  --output data/visual-audit/2024-azul-d1/review/key-reconciliation.json
```

Estados: `matched` (identidade e resposta encontradas, fonte declarada verificada, sem conflito), `needs_review` (ausência/ambiguidade/anulação/fonte pendente) e `blocked` (conflito, caderno divergente ou identidade duplicada). **matched não equivale a conteúdo visual/textual aprovado** e `publication_authorized` é sempre falso nesta fase.

A versão atual não preenche automaticamente `correct_option` no arquivo de revisão, não calcula TRI e não publica questões. Ainda é necessário auditar a origem real do gabarito e medir os erros do pipeline em uma amostra revisada.
