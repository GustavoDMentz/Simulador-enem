# Plano de fidelidade da estimativa TRI

## Implementado no PR #21
- Modelo logístico 3PL com máxima verossimilhança numérica; busca global em grade e refinamento local para evitar depender da unimodalidade.
- Estimativa por área, com opção de restringir o ano; amostras de 10, 20, 30 ou 45 questões.
- Erro-padrão aproximado baseado na informação de Fisher (não é intervalo de confiança calibrado).
- Padrões extremos (todos certos ou todos errados) não recebem theta MLE finito artificial.
- Preservação dos gabaritos locais e indicação de que os parâmetros externos não são certificados.
- A estimativa exibida é theta latente; nenhuma nota ENEM 0–1000 é fabricada.

## Limites metodológicos relevantes
1. Os parâmetros a/b/c vêm de staging externo associado por CO_ITEM e área, **não de uma certificação independente de arquivos de itens do Inep**. Confirmar origem, transformação e convenção de D (1 ou 1,7) antes de afirmar equivalência à escala oficial.
2. Um subconjunto aleatório de itens não reproduz o desenho da prova, nem sua distribuição de dificuldade/discriminação. O erro-padrão tende a ser maior com menos itens.
3. Misturar anos pode ser inadequado sem evidência de ligação/equalização entre escalas. A seleção por ano reduz esse risco, mas não prova calibração.
4. Itens com imagem são excluídos desta interface textual; LC pode incluir diferenças de idioma, ainda não modeladas.
5. Estimar theta por MLE não determina por si só a transformação para a nota oficial. A calibração e a política de tratamento de extremos exigem documentação específica do Inep e validação empírica.
6. A informação de Fisher produz somente uma aproximação local da incerteza; não se deve comunicar como margem oficial da nota.

## Próximas validações com dados Inep
- Cotejar CO_ITEM, ano, área, parâmetros e versão de calibração diretamente com os microdados e dicionários oficiais disponíveis; registrar diferenças e cobertura.
- Confirmar a parametrização e a escala de proficiência dos itens, inclusive a constante logística D.
- Reconstituir resultados em provas completas, comparando com notas oficiais anonimizadas quando os microdados permitirem vincular respostas, itens e notas, respeitando a licença e a privacidade.
- Só habilitar a escala 0–1000 depois de medir viés, erro absoluto, cobertura e comportamento nos extremos em anos separados de validação.
- Implementar renderização confiável de figuras antes de admitir itens dependentes de imagem.

**Estado:** simulado experimental, não reproduz o processo operacional de correção do Inep.
