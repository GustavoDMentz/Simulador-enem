# Simulador ENEM 2.0 — contrato de produto e implementação

Status: direção aprovada; especificação inicial, sujeita a validação com provas e microdados reais.

## Objetivo

Construir um simulador gratuito/de baixo custo, com questões fiéis aos cadernos oficiais do INEP, alternativas acessíveis, análise de desempenho fundamentada na Teoria de Resposta ao Item (TRI) e um minitutor Gemini opcional. A interface de resolução será limpa: enunciado, mídia original, cinco alternativas quando aplicável, navegação e envio da resposta. Métricas e tutoria ficam em painéis expansíveis.

## Regras de integridade

1. Nunca publicar recortes de PDF automaticamente: exigir revisão de enunciado, imagem, alternativas, numeração e gabarito.
2. Toda questão deve ter proveniência: ano, aplicação, dia, cor/caderno, número original, página(s), URL/fonte e SHA-256 do PDF.
3. Separar dados oficiais, dados derivados, estimativas e exemplos fictícios. Não rotular parâmetros estimados como oficiais.
4. A calibração 3PL (a, b, c) requer dados e metodologia apropriados; não inferir parâmetros confiáveis apenas de gabarito ou taxa de acerto.
5. A pontuação TRI apresentada ao aluno será **estimativa**, com metodologia, cobertura, limitações e versão do modelo. Sem base suficiente, exibir apenas estatísticas descritivas.
6. O tutor só explica com base no conteúdo revisado e no gabarito validado; não pode editar respostas, parâmetros ou fontes oficiais.
7. Evitar enviar dados pessoais ao provedor do LLM; manter custos controlados por opt-in, limite de chamadas e cache de explicações genéricas.
8. PDFs oficiais e recortes gerados não devem ser versionados indiscriminadamente; preservar links, hashes e manifestos. Verificar termos de uso e atribuição antes de distribuir conteúdo.

## Modelo de dados proposto

- `Exam`: id, year, application, day, booklet_color, source_url, source_sha256, answer_key_source.
- `Question`: id, exam_id, original_number, language_variant (nullable), area, topic (nullable), stem, alternatives, correct_option, page_refs, image_refs, review_status.
- `Asset`: id, source_sha256, page, bbox, mime, path, checksum, review_status.
- `ItemCalibration`: question_id, model (3PL), a, b, c, scale, sample, source, methodology, calibration_version, status (official|estimated), validated_at.
- `Attempt`: session_id, question_id, selected_option, answered_at, elapsed_seconds (optional).
- `TutorInteraction`: session_id, question_id, mode (hint|steps|concept), prompt_version, model, tokens/cost (optional), timestamp.

**Atenção:** distinguir questão exibida, item psicométrico e variante de língua; não presumir identidade apenas pelo número ou pela cor do caderno. Os IDs devem permitir mapear cadernos equivalentes e versões distintas.

## Marcos incrementais

### M1 — Questões verificáveis
- Executar pipeline visual em caderno oficial e revisar os 90 itens, incluindo língua estrangeira, conteúdo entre colunas, figuras e alternativas.
- Produzir relatório por item: encontrado, imagem íntegra, alternativas completas, gabarito validado, revisão pendente/aprovada.
- Exportar JSON validado para uso no frontend, sem depender de ArangoDB para a etapa de auditoria.

### M2 — Interface de resolução
- Enunciado, imagem original, alternativas A–E, avanço/retorno, progresso e acessibilidade.
- Registrar tentativas e mostrar acertos por área/assunto; manter histórico sem expor dados sensíveis.

### M3 — TRI com proveniência
- Investigar cobertura e significado dos campos dos microdados oficiais.
- Só calcular proficiência quando houver calibração e escala apropriadas. Implementar testes de plausibilidade e documentação científica.
- Exibir curva característica do item e explicação de a, b, c apenas quando existirem parâmetros defensáveis.

### M4 — Tutor Gemini
- API no servidor, chave em variável de ambiente, cotas e cache; nunca expor credenciais no navegador.
- Dica sem revelar resposta, explicação por etapas e revisão conceitual; gabarito validado é a referência.
- Avaliar qualidade e custo com conjunto fixo de questões antes de liberar amplamente.

## Critérios de aceite iniciais

- Nenhuma alteração em `main` ou no banco existente sem autorização.
- A publicação de questões exige validação humana; a contagem 90/90 sozinha não comprova qualidade.
- Dados TRI ausentes não são preenchidos artificialmente.
- O tutor é opcional; a resolução funciona sem IA.
- Testes automatizados e evidências de execução acompanham cada marco.
