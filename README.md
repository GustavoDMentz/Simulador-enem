<div align="center">

# 📝 Simulador ENEM

### Portal de Simulado & Análise TRI — Teoria de Resposta ao Item

[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![ArangoDB](https://img.shields.io/badge/ArangoDB-Local-DDE072?style=flat-square)](https://arangodb.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)
[![Provas](https://img.shields.io/badge/Provas_ENEM-2017--2025-E53935?style=flat-square)](https://www.gov.br/inep)
[![Status](https://img.shields.io/badge/Status-WIP-orange?style=flat-square)]()

</div>

> Pipeline completo de extração e processamento de provas do ENEM (2017–2025) integrado a um simulador web interativo de alto padrão, com análise dos parâmetros TRI, recorte dinâmico de imagens dos cadernos oficiais e assistente pedagógico por IA (Google Gemini).

> [!WARNING]
> **Status do Projeto:** Em desenvolvimento ativo (WIP). Contém erros conhecidos e ajustes pendentes na extração e mapeamento de dados de alguns anos/cadernos. Não deve ser considerado versão finalizada para produção.

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação](#-instalação)
- [Executando o Simulador](#-executando-o-simulador)
- [Pipeline de Dados](#-pipeline-de-dados)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Contribuindo](#-contribuindo)

---

## ✨ Funcionalidades

### 🖥️ Simulador Web Premium

Interface desenvolvida com **CSS puro**, tipografia [Outfit](https://fonts.google.com/specimen/Outfit) (Google Fonts), sombras dinâmicas e transições fluidas.

| Funcionalidade | Descrição |
|----------------|-----------|
| **Marca-texto Pedagógico** | Selecione qualquer trecho do enunciado ou texto-base com o mouse para destacar em amarelo fluorescente |
| **Eliminador de Alternativas** | Risca e esmaece alternativas descartadas, bloqueando-as de nova seleção (estilo "tesourinha" do ENEM físico) |
| **Busca Direta Inteligente** | Localiza qualquer questão de 1 a 180 — traduz automaticamente numerações do Dia 2 (ex: questão 35 do Dia 2 → questão oficial 125) |
| **Navegação Sequencial** | Avança automaticamente pela lista lateral e gerencia paginação de forma transparente |

### 📊 Painel TRI — Teoria de Resposta ao Item

Exibe os três parâmetros matemáticos oficiais do ENEM ao submeter uma resposta:

| Parâmetro | Nome | Interpretação |
|-----------|------|---------------|
| **a** | Discriminação | Poder da questão de diferenciar proficiências |
| **b** | Dificuldade | Barra bidirecional: azul (b < 0, fácil) → vermelho (b > 0, difícil) |
| **c** | Acerto Casual | Probabilidade de acerto por chute puro |

### 🤖 Assistente Pedagógico (Gemini 2.5 Flash)

Integração direta com a API REST do Google Gemini para feedback instantâneo em três modos:

- **Análise de Erro** — Explica a lógica incorreta e a "pegadinha" da questão quando o estudante erra
- **Gabarito Justificado** — Destrincha por que a resposta correta é verdadeira e por que os outros 4 distratores são falsos
- **Resumo Teórico** — Revisão conceitual do conteúdo cobrado na questão

### 🖼️ Pipeline de Recorte de Imagens (PyMuPDF)

Extração inteligente dos enunciados diretamente dos PDFs oficiais do INEP:

- **Detecção dinâmica de coluna** — Identifica layout em coluna simples ou largura inteira (full-width) para não cortar tabelas e gráficos pela metade
- **Delimitação precisa** — Ignora cabeçalhos azuis e bullets decorativos; delimita o corte pelo início da alternativa A ou cabeçalho da próxima questão
- **Recuperação de fontes corrompidas** — Detecta páginas com tabelas `/ToUnicode` corrompidas via taxa de sobreposição lexicográfica e aplica reversão de texto (proteção contra caracteres fantasma `™`)

---

## 📂 Estrutura do Projeto

```
Simulador-enem/
│
├── data/
│   ├── extracted/          # Imagens recortadas das questões (por ano e caderno)
│   │   ├── 2017/
│   │   ├── 2018/
│   │   └── ...2025/
│   └── fused/              # Arquivos JSONL unificados (texto + TRI + metadados)
│       ├── questoes_enem_2017_AZUL_D1.jsonl
│       └── ...
│
├── scripts/                # Pipeline de extração e processamento
│   ├── crop_and_link_images.py     # Algoritmo de visão e recorte do PDF
│   ├── etl_tri.py                  # Extração dos parâmetros TRI (microdados INEP)
│   ├── fuse.py                     # Fusão de texto + TRI → JSONL final
│   ├── deduplicate_db.py           # Remove questões duplicadas entre cores de caderno
│   ├── restore_poem_newlines.py    # Reconstrói quebras de linha em poemas e textos
│   ├── load_arangodb.py            # Carga dos JSONLs no ArangoDB
│   └── batch_process_*.py          # Scripts de processamento em lote por ano
│
├── web/                    # Aplicação Web
│   ├── server.js           # API REST Express + proxy Gemini
│   ├── package.json
│   └── public/             # Frontend estático
│       ├── index.html      # Estrutura do portal
│       ├── style.css       # Estilos, temas e transições
│       └── app.js          # Lógica de interatividade e marcações
│
├── run_pipeline.py         # Orquestrador geral do pipeline
└── README.md
```

---

## ⚙️ Instalação

### Pré-requisitos

| Ferramenta | Versão mínima | Verificação |
|------------|---------------|-------------|
| Node.js | 18+ | `node -v` |
| Python | 3.10+ | `python3 --version` |
| ArangoDB | 3.11+ | Rodando em `localhost:8529` |

### 1. Clone o repositório

```bash
git clone https://github.com/GustavoDMentz/Simulador-enem.git
cd Simulador-enem
```

### 2. Instale as dependências do servidor web

```bash
cd web
npm install
```

### 3. Configure as variáveis de ambiente

Crie o arquivo `web/.env`:

```env
PORT=3000
GEMINI_API_KEY=sua_chave_google_ai_studio_aqui
ARANGO_HOST=http://localhost:8529
DB_NAME=enem
```

> 💡 Chave gratuita em: [aistudio.google.com](https://aistudio.google.com)

### 4. (Opcional) Instale as dependências Python para o pipeline

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pymupdf pandas numpy
```

---

## ▶️ Executando o Simulador

```bash
cd web
npm start
```

Acesse em: **http://localhost:3000**

---

## 🔄 Pipeline de Dados

O pipeline transforma os PDFs oficiais do INEP em dados estruturados prontos para o simulador:

```
PDFs Oficiais (INEP)
    ↓
[crop_and_link_images.py]  → Recorta e salva imagens das questões
    ↓
[etl_tri.py]               → Extrai parâmetros TRI dos microdados
    ↓
[fuse.py]                  → Unifica texto + TRI → JSONL
    ↓
[load_arangodb.py]         → Carrega no ArangoDB
    ↓
Simulador Web              → Consulta e exibe para o estudante
```

### Comandos do pipeline

```bash
# Ativar o ambiente virtual Python
source .venv/bin/activate

# Orquestrador completo (recomendado)
python3 run_pipeline.py

# Re-recortar imagens com precisão máxima
python3 scripts/crop_and_link_images.py --force

# Deduplicar questões entre cadernos de cores diferentes
python3 scripts/deduplicate_db.py

# Carregar dados no ArangoDB
python3 scripts/load_arangodb.py
```

---

## 🔐 Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `PORT` | Porta do servidor Express | `3000` |
| `GEMINI_API_KEY` | Chave da API do Google Gemini | `AIzaSy...` |
| `ARANGO_HOST` | Endereço do ArangoDB | `http://localhost:8529` |
| `DB_NAME` | Nome do banco de dados | `enem` |

---

## 🗓️ Cobertura de Dados

| Ano | Dias | Cadernos |
|-----|------|----------|
| 2017–2023 | Dia 1 + Dia 2 | AMARELO, AZUL, BRANCO, CINZA, ROSA |
| 2024–2025 | Dia 1 + Dia 2 | AZUL |

> ⚠️ A cobertura de cadernos varia por ano conforme disponibilidade dos PDFs e estágio de processamento.

---

## 🤝 Contribuindo

Contribuições são bem-vindas, especialmente para:

- 🐛 Correções de extração em anos/cadernos com problemas conhecidos
- 📄 Adição de cadernos ainda não processados (2024–2025 incompletos)
- 🎨 Melhorias na interface do simulador
- 📊 Novos gráficos e visualizações TRI

Abra uma [issue](https://github.com/GustavoDMentz/Simulador-enem/issues) ou um pull request!

---

## 📄 Licença

MIT — uso livre para fins educacionais e de pesquisa.
