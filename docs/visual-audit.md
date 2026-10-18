# Auditoria visual dos PDFs do ENEM

Ferramenta inicial de diagnóstico, sem acesso ao ArangoDB e sem chamadas de IA.

## Executar

Instale PyMuPDF no ambiente Python:

```bash
python -m pip install pymupdf
python scripts/audit_pdf_visuals.py --pdf "/caminho/para/prova.pdf" --output data/visual-audit/2025-azul-d1
```

Abra `data/visual-audit/2025-azul-d1/index.html` no navegador.

A ferramenta gera:

- `manifest.json`: nome e SHA-256 do PDF, número de páginas, caixas de imagens raster e contagem de desenhos vetoriais por página.
- `page_XXX.png`: renderização integral de cada página, sem perda de elementos vetoriais/textuais no recorte.
- `index.html`: revisão visual das páginas.

**Limitação intencional:** esta etapa inventaria páginas, mas ainda não identifica o contorno de cada questão, não extrai figuras individuais e não valida correspondência entre figura e questão. Isso exige uma etapa seguinte de segmentação e testes com provas reais. Nenhum documento do banco é alterado.

**Atenção:** PDFs e prévias podem ser grandes. Use `--dpi 120` inicialmente; aceita valores entre 72 e 300. Não publique PDFs ou recortes sem verificar os direitos e as condições de redistribuição.
