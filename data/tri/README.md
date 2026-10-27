# Base independente de parâmetros TRI

Este diretório armazena exclusivamente parâmetros **verificados** de itens ENEM. A base inicia vazia: ausência de dados não autoriza estimativas ou preenchimento automático.

Formato JSONL (um objeto por linha):

```json
{"ano":2023,"co_item":123456,"area_conhecimento":"MT","gabarito_oficial":"C","a":1.25,"b":0.7,"c":0.2,"fonte":"INEP ITENS_PROVA_2023","status":"VERIFIED"}
```

O exemplo acima é **fictício**, apenas documentação, e não deve ser importado como dado real.

Critérios mínimos: identificar o item por `ano + co_item`, conferir área e gabarito, exigir valores finitos, `a > 0`, `0 <= c <= 1`, e rejeitar chaves duplicadas ou conflitantes. Manter `parametros_tri: null` para itens sem comprovação.

Os arquivos oficiais originais não devem ser substituídos por parâmetros estimados.
