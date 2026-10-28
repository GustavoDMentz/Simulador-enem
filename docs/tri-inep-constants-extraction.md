# Extração verificável das constantes do microEnem

A transformação no pacote do Inep é `round(theta * k + d, 1)`, por área.

**Não inserir valores manualmente a partir de tabelas secundárias.** Execute com R instalado e conexão à internet:

```r
download.file("https://raw.githubusercontent.com/inepoficial/microEnem/master/data/constantes.rda",
              "constantes.rda", mode="wb")
load("constantes.rda")
stopifnot(is.data.frame(constantes))
print(constantes)
stopifnot(all(c("area", "k", "d") %in% names(constantes)))
stopifnot(all(c("LC", "CH", "CN", "MT") %in% constantes$area))
```

Depois de conferir os quatro pares, transcrever para JSON versionado com URL, commit SHA e checksum SHA-256 da fonte, e adicionar testes que comparem `round(theta*k+d,1)` em cada área. O simulador não deve chamar esse resultado de oficial enquanto os itens não estiverem comprovadamente na escala correta.

Referência: https://github.com/inepoficial/microEnem/blob/master/R/calc.nota.R

Uma dissertação hospedada no Inep apresenta constantes por área, mas é necessário confrontá-las com o RData utilizado pelo pacote antes de adotá-las: https://riep.inep.gov.br/server/api/core/bitstreams/9b52574b-7fe6-4d6d-9ea6-ca1d151a151e/content
