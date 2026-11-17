<div align="center">

# Simulador ENEM
### Questões reais. Revisão rastreável. Prática sem atalhos.

**Um simulador de questões do ENEM com correção, recursos de estudo e um processo explícito de auditoria das provas oficiais.**

[![Testes Python](https://github.com/GustavoDMentz/Simulador-enem/actions/workflows/enem-python-tests.yml/badge.svg)](https://github.com/GustavoDMentz/Simulador-enem/actions/workflows/enem-python-tests.yml)
[![Integridade do banco](https://github.com/GustavoDMentz/Simulador-enem/actions/workflows/db-integrity.yml/badge.svg)](https://github.com/GustavoDMentz/Simulador-enem/actions/workflows/db-integrity.yml)
![Questões auditadas](https://img.shields.io/badge/quest%C3%B5es%20auditadas-1611%20%2F%201620-2ea44f)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org/)

[Começar](#comece-em-poucos-passos) · [Cobertura](#cobertura-atual) · [Auditoria](#uma-questão-só-vale-pontos-quando-é-confiável) · [Estrutura](#por-dentro-do-projeto) · [Contribuir](#contribuindo)

</div>

---

## O que é este projeto?

O **Simulador ENEM** reúne uma aplicação web para resolver questões e um pipeline de extração, conferência e publicação de conteúdo das provas do Inep. O foco não é exibir um banco enorme, e sim saber **quais questões podem ser corrigidas com confiança**.

A aplicação oferece navegação por questões, seleção de respostas, eliminação de alternativas e recursos de apoio ao estudo. A camada de dados guarda a origem de cada item e impede que questões ainda não revisadas entrem na pontuação.

## Cobertura atual

O alvo é o **caderno azul da aplicação regular, de 2017 a 2025**: 9 provas × 180 posições = **1620**. Hoje **1611 posições (99,4%)** estão autorizadas para pontuação.

| Ano | Autorizadas | Ano | Autorizadas | Ano | Autorizadas |
| :-: | :-: | :-: | :-: | :-: | :-: |
| 2017 | 180 / 180 | 2018 | 179 / 180 | 2019 | 180 / 180 |
| 2020 | 179 / 180 | 2021 | 179 / 180 | 2022 | 179 / 180 |
| 2023 | 179 / 180 | 2024 | 179 / 180 | 2025 | 177 / 180 |

As **9 posições restantes são questões anuladas pelo Inep**, que não valem pontos e por isso ficam de fora: 2018 D2 Q163, 2020 D2 Q157, 2021 D2 Q138, 2022 D2 Q157, 2023 D2 Q164, 2024 D2 Q129 e 2025 D2 Q123, Q132 e Q174.

Nas posições de língua estrangeira (inglês ou espanhol), só a versão em inglês conta, com o gabarito do idioma. Cada questão mantém o recorte original do PDF oficial e uma descrição em texto para leitores de tela (ver [Acessibilidade](#acessibilidade)).

> [!IMPORTANT]
> Estes números descrevem o catálogo auditado. Não são uma certificação do Inep, não equivalem à nota oficial do exame e não significam que a aplicação esteja implantada em produção.

## O que você encontra aqui

| Para estudar | Para confiar nos dados |
| --- | --- |
| Resolução e correção de questões | Gabaritos confrontados com fontes oficiais |
| Navegação e seleção de alternativas | Identidade de cada item conferida no ITENS_PROVA oficial |
| Marca-texto e eliminação de opções | Registro de origem, hashes e decisões de auditoria |
| Descrições de figuras para leitores de tela | Publicação bloqueada por padrão para itens inconclusivos |
| Informações TRI quando disponíveis | Parâmetros TRI não certificados permanecem ausentes (`null`) |

### Do PDF à tela

```text
Provas e gabaritos do Inep
          │
          ▼
 Extração e recorte das questões
          │
          ▼
 Conferência: identidade, gabarito, recorte
          │
          ├── Inconclusivo ──► Quarentena (sem pontuação)
          │
          ▼
 Evidências e hashes verificados
          │
          ▼
 Manifesto de publicação autorizada
          │
          ▼
       Simulador
```

## Comece em poucos passos

**Requisitos:** Node.js 18+, Python 3.10+ para os scripts e uma instância ArangoDB compatível para os fluxos que dependem do banco.

```bash
git clone https://github.com/GustavoDMentz/Simulador-enem.git
cd Simulador-enem/web
npm install
npm start
```

Abra **http://localhost:3000**.

O servidor pode exigir ArangoDB e variáveis de ambiente conforme os recursos usados. Para o desenvolvimento local, crie `web/.env`:

```dotenv
PORT=3000
ARANGO_HOST=http://localhost:8529
DB_NAME=enem
GEMINI_API_KEY=
```

A chave Gemini do servidor é opcional e **não deve ser versionada**. Confira os nomes e requisitos no código do servidor antes de implantar.

### Explicação por IA com a sua própria chave (BYOK)

Quem usa o simulador não precisa de nada instalado nem de chave no servidor: depois de responder uma questão, o painel **🔑 Sua chave do Gemini** (logo abaixo de "Explicar com IA") ensina a criar uma chave gratuita no [Google AI Studio](https://aistudio.google.com/apikey) e a colá-la.

- A chave fica **só no navegador** de quem a colou (`localStorage`) e pode ser removida a qualquer momento.
- Ela viaja apenas no cabeçalho `x-gemini-key` de cada pedido de explicação, para ser repassada ao Google; o servidor não a grava nem a registra em log.
- Se existir `GEMINI_API_KEY` no servidor, ela serve de padrão para quem não informar a própria chave.
- Sem nenhuma chave, ou com chave recusada pelo Google, a tela abre o painel e explica o que fazer, em vez de mostrar um erro técnico.

### Executar as verificações

```bash
# Na raiz: testes Python
python3 -m pytest

# Testes Node (como no CI)
node --test web/tests/*.test.js
```

Alguns fluxos exigem serviços adicionais; os comandos completos de CI estão em [`.github/workflows/`](.github/workflows/).

## Uma questão só vale pontos quando é confiável

O **audit gate** é a principal garantia do projeto. Uma questão só é publicada quando seu registro traz autorização explícita e evidências consistentes de **identidade**, **gabarito** e **recorte** (texto, alternativas, figuras e créditos).

- **Aprovada:** pode ser selecionada e corrigida pelo simulador.
- **Pendente:** aparece na prévia de revisão, mas não conta pontos.
- **Inconsistente:** mudança inesperada em conteúdo, hash ou imagem impede a publicação.

A política é **fail-closed**: na dúvida, não publica. Para entrar, o `TX_GABARITO` do ITENS_PROVA, o gabarito do PDF oficial e o gabarito publicado precisam coincidir, e o recorte precisa passar nas verificações visuais (alternativas A–E em sequência, cabeçalho da própria questão, nenhuma tinta de outra questão sobreposta).

**Onde acompanhar:** [manifesto de auditoria](data/audit/manifest.json) · [resolução de identidade](docs/identity-resolution.md) · [histórico de validação](docs/validation-progress.md) · [fluxo dos lotes](docs/verified-batch-workflow.md) · relatórios por lote em `docs/enem-audit-batch-NN.md`.

<details>
<summary><b>Linha do tempo dos lotes</b></summary>

| Lote | Marco |
| --- | --- |
| 08 | 181 questões recuperadas e verificadas em desktop e celular; [relatório](docs/enem-audit-batch-08.md) |
| 09–11 | Texto puro com identidade resolvida pelo ITENS_PROVA oficial; [lote 09](docs/enem-audit-batch-09.md), [10](docs/enem-audit-batch-10.md), [11](docs/enem-audit-batch-11.md) |
| 12–32 | Expansão por ano e por tipo de questão, sempre preservando byte a byte as linhas anteriores |
| 33 | 42 candidatas antes reprovadas voltam com recorte corrigido; [relatório](docs/enem-audit-batch-33.md) |
| 34 | Posições de idioma e texto compartilhado; chega a 1611; [relatório](docs/enem-audit-batch-34.md) |

</details>

### E a TRI?

A Teoria de Resposta ao Item usa parâmetros de discriminação (`a`), dificuldade (`b`) e acerto casual (`c`). O repositório tem ferramentas para trabalhar com esses dados, mas **não presume que qualquer associação de parâmetros seja oficial ou validada**. Sem comprovação suficiente, os parâmetros ficam `null`. Acertar questões no simulador não equivale a obter uma nota oficial do ENEM.

## Acessibilidade

Cada questão exibida como recorte da prova traz uma descrição específica para leitores de tela: identificação da questão, conteúdo do recorte, figura descrita em texto, alternativas quando só existem na imagem e o texto-base. A camada de apresentação (`data/audit/question-presentation.json`) fica **separada** dos registros auditados e não altera gabarito nem conteúdo. Os limites (leitura sem OCR, valores densos de gráficos aproximados) estão em [docs/question-rendering.md](docs/question-rendering.md).

## Por dentro do projeto

| Diretório | Responsabilidade |
| --- | --- |
| `web/` | Servidor Express, endpoints, interface e testes Node |
| `data/blue-published/` | Catálogo publicado (questões autorizadas) |
| `data/audit/` | Manifesto, evidências, identidades e relatórios de lote |
| `data/extracted/` | Recortes e imagens verificados |
| `scripts/` | Extração, auditoria, reconciliação e carregamento |
| `tests/` | Testes Python dos lotes, da identidade e da apresentação |
| `docs/` | Procedimentos, decisões e limites da validação |
| `.github/workflows/` | Verificações automatizadas e aquisição histórica |

**Tecnologias:** JavaScript/Node.js, Express, Python, ArangoDB, PyMuPDF e integração opcional com Google Gemini. O frontend usa HTML, CSS e JavaScript.

### Aquisição das provas oficiais

O pipeline cobre as provas regulares de **2017 a 2025**, com atenção às variantes de caderno e de língua estrangeira. A aquisição histórica é **manual** e independente da publicação das questões já verificadas.

> [!NOTE]
> O downloader oficial encontrou falhas de confiança TLS na conexão com o Inep em ambiente de CI. O problema está documentado: não se desativa a verificação HTTPS nem se declara sucesso com fontes ausentes.

## Contribuindo

Ajuda é bem-vinda na revisão de questões, correção de recortes, acessibilidade, testes e documentação.

Antes de propor a aprovação de uma questão, inclua a identificação da prova, a fonte consultada, o que foi corrigido e as evidências da mudança. Não envie gabaritos inferidos por IA como se fossem oficiais.

[Abra uma issue](https://github.com/GustavoDMentz/Simulador-enem/issues) ou [proponha um pull request](https://github.com/GustavoDMentz/Simulador-enem/pulls).

## Limites e transparência

Este é um **projeto independente**, sem afiliação ou endosso do Inep. As provas e gabaritos oficiais pertencem aos respectivos titulares, e este repositório não altera os direitos sobre materiais de terceiros.

O projeto segue em evolução: o histórico de aquisição pode depender de fontes externas e não há promessa de equivalência entre a pontuação local e a nota oficial.

---

<div align="center">

**Menos questões duvidosas. Mais estudo com evidências.**

[Repositório](https://github.com/GustavoDMentz/Simulador-enem) · [Documentação](docs/) · [Testes e CI](https://github.com/GustavoDMentz/Simulador-enem/actions)

</div>
