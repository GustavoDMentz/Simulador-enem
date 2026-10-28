# Compatibilidade com microEnem (Inep)

Referências primárias:
- https://github.com/inepoficial/microEnem/blob/master/R/calc.nota.R
- https://github.com/inepoficial/microEnem/blob/master/R/mod.caderno.R
- https://github.com/inepoficial/microEnem/blob/master/data/constantes.rda

O modelo mirt recebe a1=a e d=-a*b; logo a probabilidade 3PL usa exp(a*(theta-b)), sem multiplicador 1,7. O método de pontuação descrito é EAP, prior N(0,1), 40 pontos em [-4,4]. A grade do simulador foi alinhada a esses extremos.

A transformação final no pacote oficial é nota=round(k_area*theta+d_area,1), com constantes por área do objeto binário constantes.rda. Essas constantes **não foram extraídas nem verificadas nesta alteração**; por isso não é lícito chamar 500+100*theta de nota oficial. O índice atual é explicitamente ilustrativo.

Pendências para equivalência maior: importar constantes oficiais do RData com proveniência; confirmar que parâmetros externos coincidem com a parametrização dos microdados; tratar idioma, anulações, brancos e calibração dos itens; conferir numericamente o algoritmo EAP contra mirt.

Sem essas condições, exibir apenas índice experimental e theta, nunca uma nota certificada.

## Constantes publicadas em pesquisa hospedada pelo Inep
Tabela 7 (k, d): LC (499.978,108.086); CH (501.489,112.310); CN (501.144,113.102); MT (500.020,129.646). Fonte: https://riep.inep.gov.br/server/api/core/bitstreams/9b52574b-7fe6-4d6d-9ea6-ca1d151a151e/content

Esses valores são de uma pesquisa no repositório institucional, e **não foram confrontados byte a byte com constantes.rda**. O aplicativo os utiliza para transformar theta em uma faixa arredondada às dezenas, baseada em aproximadamente 80% de massa posterior (aproximação normal ±1,28155 desvio-padrão). A faixa não mede o erro de calibração nem é intervalo de cobertura empiricamente demonstrado. Não é nota oficial.
