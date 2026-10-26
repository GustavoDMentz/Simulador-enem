<div align="center">

# Simulador ENEM
### Questões reais. Revisão rastreável. Prática sem atalhos.

**Um simulador de questões do ENEM com correção, recursos de estudo e um processo explícito de auditoria das provas oficiais.**

[![Python checks](https://github.com/GustavoDMentz/Simulador-enem/actions/workflows/python-checks.yml/badge.svg)](https://github.com/GustavoDMentz/Simulador-enem/actions)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org/)
[![License](https://img.shields.io/badge/licen%C3%A7a-MIT-64748b)](LICENSE)

[Começar a usar](#comece-em-poucos-passos) · [Como funciona a auditoria](#uma-questão-só-vale-pontos-quando-é-confiável) · [Arquitetura](#por-dentro-do-projeto) · [Contribuir](#contribuindo)

</div>

---

## O que é este projeto?

O **Simulador ENEM** reúne uma aplicação web para resolver questões e um pipeline de preparação, conferência e publicação de conteúdo extraído de provas do Inep. O foco não é simplesmente exibir um banco enorme: é saber **quais questões podem ser corrigidas com confiança**.

A aplicação oferece navegação por questões, seleção de respostas, eliminação de alternativas e recursos de apoio ao estudo. A camada de dados mantém evidências de origem e impede que itens ainda não revisados entrem na pontuação.

> [!IMPORTANT]
> **Estado da auditoria — 25/10/2026:** no lote de 513 questões da prévia, **59 foram revisadas e autorizadas para pontuação**; **454 permanecem em quarentena**. Esses números descrevem o lote auditado, não toda a cobertura histórica do repositório. Não são uma certificação do Inep nem significam que a aplicação esteja implantada em produção.

## O que você encontra aqui

| Para estudar | Para confiar nos dados |
| --- | --- |
| Resolução e correção de questões | Gabaritos confrontados com fontes oficiais |
| Navegação e seleção de alternativas | Revisão de textos, fórmulas, imagens e créditos |
| Marca-texto e eliminação de opções | Registro de origem, hashes e decisões de auditoria |
| Recursos pedagógicos e integração opcional com IA | Publicação bloqueada por padrão para itens inconclusivos |
| Visualização de informações TRI quando disponíveis | Parâmetros TRI não certificados permanecem ausentes (`null`) |

### Uma prévia do fluxo

```text
Provas e gabaritos do Inep
          │
          ▼
 Extração e organização
          │
          ▼
 Revisão de conteúdo e gabarito
          │
          ├── Inconclusivo ──► Quarentena (sem pontuação)
          │
          ▼
 Evidências e integridade verificadas
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

O servidor pode exigir ArangoDB e variáveis de ambiente conforme os recursos utilizados. Para configurar a integração local, crie `web/.env` com os valores apropriados para o seu ambiente:

```dotenv
PORT=3000
ARANGO_HOST=http://localhost:8529
DB_NAME=enem
GEMINI_API_KEY=
```

A chave Gemini é opcional para a integração pedagógica e **não deve ser versionada**. Confira os nomes e requisitos efetivos no código do servidor antes de implantar; este exemplo é para desenvolvimento local.

### Executar verificações

```bash
# Na raiz do repositório: testes Python
python3 -m pytest

# Testes de auditoria da API
cd web
node --test tests/audit-gate.test.js
```

Algumas verificações exigem dependências ou serviços adicionais. Consulte os workflows em [GitHub Actions](https://github.com/GustavoDMentz/Simulador-enem/actions) para os comandos completos de CI.

## Uma questão só vale pontos quando é confiável

O **audit gate** é a principal garantia do projeto. Uma questão só pode ser publicada quando seu registro contém autorização explícita e evidências consistentes de identidade, conteúdo, alternativas, gabarito e elementos visuais.

- **Aprovada:** pode ser selecionada e corrigida pelo simulador.
- **Pendente:** continua acessível na prévia de revisão, mas não conta pontos.
- **Inconsistente:** alterações inesperadas em conteúdo, hashes ou imagens impedem a publicação.

O sistema segue uma política **fail-closed**: na dúvida, não publica. A verificação estrutural de um JSON, sozinha, não comprova fidelidade à prova.

**Onde acompanhar:** [manifesto de auditoria](data/audit/manifest.json) · [registro de restauração](data/audit/restoration-verification.json) · [histórico de validação](docs/validation-progress.md).

### E a TRI?

A Teoria de Resposta ao Item utiliza parâmetros de discriminação (`a`), dificuldade (`b`) e acerto casual (`c`). O repositório contém ferramentas para trabalhar com esses dados, mas **não presume que qualquer associação de parâmetros seja oficial ou validada**. Quando não houver comprovação suficiente, os parâmetros ficam `null`. Acertar questões no simulador não equivale a obter uma nota oficial do ENEM.

## Por dentro do projeto

| Diretório | Responsabilidade |
| --- | --- |
| `web/` | Servidor Express, endpoints, interface e testes Node |
| `data/fused/` | Registros estruturados legados de questões |
| `data/audit/` | Manifesto, evidências e controle de publicação |
| `scripts/` | Extração, auditoria, reconciliação e carregamento |
| `docs/` | Procedimentos, decisões e limites da validação |
| `.github/workflows/` | Verificações automatizadas e aquisição histórica |

**Tecnologias:** JavaScript/Node.js, Express, Python, ArangoDB, PyMuPDF e integração opcional com Google Gemini. O frontend usa HTML, CSS e JavaScript.

### Aquisição das provas oficiais

O pipeline contempla provas regulares de **2017 a 2025**, com atenção às variantes de caderno e língua estrangeira. A aquisição histórica é uma tarefa **manual e independente** da publicação das questões já verificadas.

> [!NOTE]
> O downloader oficial encontrou falhas de confiança TLS na conexão com o Inep em ambiente de CI. O problema está documentado; não se desativa a verificação HTTPS nem se declara sucesso com fontes ausentes. A auditoria das questões já restauradas é controlada separadamente.

## Contribuindo

Ajuda é bem-vinda na revisão de questões, correção de recortes, acessibilidade da interface, testes e documentação.

Antes de propor a aprovação de uma questão, inclua a identificação da prova, a fonte consultada, o que foi corrigido e as evidências que sustentam a mudança. Não envie gabaritos inferidos por IA como se fossem oficiais.

[Abra uma issue](https://github.com/GustavoDMentz/Simulador-enem/issues) ou [proponha um pull request](https://github.com/GustavoDMentz/Simulador-enem/pulls).

## Limites e transparência

Este é um **projeto independente**, sem afiliação ou endosso do Inep. As provas e gabaritos oficiais pertencem aos respectivos titulares. A licença do código não altera os direitos sobre materiais de terceiros.

O projeto ainda está em evolução: a prévia contém itens pendentes, o histórico de aquisição pode depender de fontes externas e não há promessa de equivalência entre a pontuação local e a nota oficial do exame.

---

<div align="center">

**Menos questões duvidosas. Mais estudo com evidências.**

[Repositório](https://github.com/GustavoDMentz/Simulador-enem) · [Documentação](docs/) · [Testes e CI](https://github.com/GustavoDMentz/Simulador-enem/actions)

</div>
