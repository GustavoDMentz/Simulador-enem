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

## Referência primária encontrada (2026-10)
- INEP, microdados ENEM: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem
- Pacote do próprio INEP `microEnem`: https://github.com/inepoficial/microEnem
- Implementação de referência: https://raw.githubusercontent.com/inepoficial/microEnem/master/R/calc.nota.R

A implementação `calc.nota` descreve **EAP**, com prior normal padrão e 40 pontos de quadratura, em vez de MLE, e utiliza constantes de transformação por área (`k`, `d`) para a escala oficial. O simulador agora oferece EAP aproximado como referência **não validada** (quadratura por pontos médios; não necessariamente idêntica à do `mirt`), além da MLE. Não copiar constantes arbitrárias nem transformar theta em nota antes de cotejar os resultados.

### Experimento reproduzível a executar com os microdados
1. Escolher 2019 e 2022, que o `microEnem` declara suportar; começar por MT, CH e CN e depois LC, observando `TP_LINGUA`.
2. Baixar do Inep `MICRODADOS_ENEM_{ano}.csv` e `ITENS_PROVA_{ano}.csv`, registrando URL, data e checksum. Não incluir respostas individuais no repositório.
3. Para cada participante com prova válida, extrair `CO_PROVA_*`, `TX_RESPOSTAS_*`, `NU_NOTA_*`, presença e idioma; preservar correspondência de caderno, posição, anuladas e gabarito.
4. Calcular a nota de referência com `microEnem::calc.nota` e comparar com `NU_NOTA_*`. Só depois comparar com o nosso 3PL EAP/MLE, usando exatamente os mesmos itens e respostas.
5. Relatar MAE, RMSE, viés, percentis do erro, cobertura, casos extremos, por área/ano e por faixa de nota; separar calibração e validação fora da amostra.
6. Avaliar `k` e `d` por área e convenção de discriminação (D=1 ou 1,7) antes de apresentar nota estimada.

**Resultado empírico neste estágio: não medido.** O pipeline de validação em milhões de respostas ainda depende de obter/processar os arquivos brutos e verificar os esquemas atuais do Inep. Os testes unitários do estimador não substituem essa comparação.
