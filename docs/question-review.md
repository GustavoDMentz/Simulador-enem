# Revisão humana e exportação de questões

A fila de revisão nasce dos recortes candidatos, não de um gabarito inferido.

```bash
python scripts/build_question_review.py \
  --pdf data/sources/2024/dia1/azul/prova.pdf \
  --candidates data/visual-audit/2024-azul-d1/questions/candidates.json \
  --output data/visual-audit/2024-azul-d1/review \
  --year 2024 --day 1 --color azul
```

Abra `review/review.html` para inspecionar os recortes e o texto extraído. O arquivo `question-review.json` é a fila de trabalho. Por padrão **tudo permanece pendente**.

Para cada registro, um revisor deve conferir visualmente o caderno e preencher:
- `stem`: enunciado final conferido;
- `alternatives`: objeto com chaves `A`, `B`, `C`, `D`, `E` e textos completos;
- `correct_option`: letra conferida contra gabarito oficial;
- `answer_key_source`: referência verificável ao gabarito usado;
- `reviewer` e `reviewed_at`: identificação e data;
- `language_variant`: `ingles` ou `espanhol` nas questões 1–5 do primeiro dia;
- `review_status`: alterar para `approved` **somente após a conferência**.

Depois exporte:

```bash
python scripts/export_reviewed_questions.py \
  --input data/visual-audit/2024-azul-d1/review/question-review.json \
  --output data/visual-audit/2024-azul-d1/review/published-questions.json
```

O exportador descarta registros pendentes ou incompletos e relata o motivo. Ele detecta IDs/questões duplicadas aprovadas e deixa `calibration: null` — parâmetros TRI serão vinculados em etapa própria, somente com fontes e metodologia apropriadas.

**Limites atuais:** aprovação é declarada manualmente no JSON; o script verifica presença e consistência básica dos campos, **não** a veracidade do gabarito, a integridade semântica da imagem, nem a correspondência dos textos ao PDF. O hash do recorte é metadado gerado na importação, não uma assinatura de aprovação. O formato ainda não é um painel de revisão com controles interativos.
