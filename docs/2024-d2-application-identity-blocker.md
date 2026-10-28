# 2024 D2 — divergência entre aplicação regular e reaplicação

Primeira fornada: 28 posições (93,97,99,102,105,106,107,108,109,116,117,120,126,129,135,140,143,149,151,156,157,159,160,162,165,171,179,180).

Fontes oficiais distintas:
- Regular: https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D2_CD7.pdf
- Reaplicação/PPL: https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_reaplicacao_PPL_D2_CD7.pdf
- Prova regular: https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D2_CD7.pdf

Comparação do campo `gabarito_oficial` no `data/fused/questoes_enem_2024_AZUL_D2.jsonl`:
- **10/28** coincidem com gabarito regular.
- **23/28** coincidem com gabarito reaplicação/PPL.
- **18/28** divergem do gabarito regular.
- **0/28** divergem de ambos os gabaritos (há coincidências entre provas).

A posição 129 é **ANULADA** no gabarito regular, mas consta B no registro local, coincidindo com reaplicação. A identidade das questões ainda exige cotejo dos textos dos PDFs de cada aplicação. **Não corrigir só a letra:** a questão pode ser de outra aplicação.

`scripts/check_2024_d2_regular_key.py` é uma verificação fail-closed da primeira fornada: retorna erro se o arquivo continuar divergente. Não modifica o banco nem publica questões.

**Decisão: QUARANTINE_APPLICATION_IDENTITY.** Não publicar como prova regular até reconstruir/confirmar identidade e texto com PDF correspondente.
