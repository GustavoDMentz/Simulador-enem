# Importação de fontes oficiais

As provas e gabaritos podem ser obtidos no portal do INEP:
https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos

Os microdados estão em:
https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem

O script abaixo **importa apenas PDFs de provas**, não os arquivos ZIP de microdados nem gabaritos.

## Importar PDF já baixado

```bash
python scripts/import_official_pdf.py --year 2025 --day 1 --color azul --file "/caminho/prova.pdf"
```

## Baixar PDF de URL oficial

```bash
python scripts/import_official_pdf.py --year 2025 --day 1 --color azul --url "https://download.inep.gov.br/..."
```

Substitua o exemplo por uma URL real obtida no site do INEP. O importador exige HTTPS e domínio inicial `gov.br`.

Os arquivos ficam em `data/sources/2025/dia1/azul/` com `prova.pdf` e `source.json` (origem, SHA-256, tamanho, data da importação). A pasta está no `.gitignore` para evitar versionar arquivos pesados.

O importador não sobrescreve fontes já cadastradas. A assinatura inicial `%PDF-` é uma verificação básica, **não uma validação completa da estrutura do PDF**. O conteúdo e a correspondência de ano/dia/cor precisam ser conferidos. O download pode seguir redirecionamentos HTTP; execute somente com URLs confiáveis. Para reimportar outra versão, use outro diretório de saída e preserve o manifesto antigo.

## Auditoria visual

```bash
python scripts/audit_pdf_visuals.py --pdf data/sources/2025/dia1/azul/prova.pdf --output data/visual-audit/2025-azul
python scripts/segment_question_candidates.py --pdf data/sources/2025/dia1/azul/prova.pdf --output data/visual-audit/2025-azul-recortes
```

Os recortes gerados são **candidatos** e requerem revisão humana antes de publicação.
