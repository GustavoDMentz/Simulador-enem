# Conferência independente de gabaritos — ENEM 2024, caderno azul

Fontes primárias fornecidas pelo mantenedor:
- `2024_GB_impresso_D1_CD1.pdf`: gabarito oficial do primeiro dia, caderno 1 azul.
- `2024_GB_impresso_D2_CD7.pdf`: gabarito oficial do segundo dia, caderno 7 azul.

Cruzamento por `ano=2024` e `posicao_prova` com `data/blue-published/questions.jsonl` (110 questões), comparando `gabarito_oficial` local e `TX_GABARITO` do CSV externo de `HenriqueLindemann/analise-enem`.

| Classificação | Contagem |
| --- | ---: |
| Local e externo concordam com gabarito oficial | 60 |
| Apenas local concorda com gabarito oficial | 50 |
| Apenas externo concorda com gabarito oficial | 0 |
| Nenhum concorda | 0 |

**Conclusão:** nas 110 questões publicadas de 2024, o gabarito local concorda com os PDFs oficiais; em 50, o gabarito externo diverge. Exemplos: questão 7: oficial/local C, externo D; questão 9: oficial/local E, externo A.

**Implicação:** NÃO sobrescrever gabaritos locais com os externos. NÃO promover automaticamente parâmetros associados a divergências; é necessário verificar se os parâmetros `a,b,c` realmente pertencem ao mesmo item `CO_ITEM`, apesar da inconsistência no campo `TX_GABARITO`.

**Escopo:** esta conferência trata apenas das 110 questões publicadas de 2024. Os outros anos exigem seus respectivos gabaritos oficiais. Os PDFs oficiais foram fornecidos na conversa e não foram copiados para o repositório.
