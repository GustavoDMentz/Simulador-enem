# Simulador ENEM & Portal de Análise TRI (Teoria de Resposta ao Item)

Um pipeline completo e simulador web interativo de alto padrão para o Exame Nacional do Ensino Médio (ENEM), integrando processamento de dados microestatísticos, extração automatizada de imagens físicas dos cadernos oficiais e suporte pedagógico personalizado por inteligência artificial (Google Gemini).

---

> [!WARNING]
> **Status do Projeto**: Este repositório está em **desenvolvimento ativo (WIP)** e contém erros conhecidos e ajustes pendentes na extração e mapeamento de dados. Não deve ser considerado uma versão finalizada de produção.

---

## 🚀 Principais Funcionalidades

### 🖥️ Simulador Web Premium
* **Interface de Alto Padrão (Aesthetics First)**: Desenvolvido com CSS puro utilizando a tipografia *Outfit* (Google Fonts), cantos suavizados, sombras dinâmicas e transições fluidas.
* **Marca-Texto Pedagógico (Highlighter)**: Selecione qualquer trecho do texto base ou enunciado com o mouse e pinte-o de amarelo fluorescente de forma nativa e robusta.
* **Eliminador de Alternativas (Tesourinha)**: Risca o texto (`line-through`) e esmaece alternativas marcadas pelo estudante como incorretas, bloqueando-as de cliques e desmarcando seleções ativas automaticamente.
* **Busca Direta Inteligente**: Campo para localizar qualquer questão de 1 a 180. Traduz automaticamente numerações relativas do Dia 2 (ex: buscar `35` no Dia 2 localiza a questão oficial `125` do caderno).
* **Navegação Sequencial**: Avança automaticamente pela lista lateral de questões e cuida da paginação de forma transparente para o usuário.

### 📊 Painel Métrico TRI (Teoria de Resposta ao Item)
Visualização gráfica dos três parâmetros matemáticos oficiais do ENEM após submeter a resposta:
1. **Parâmetro $a$ (Discriminação)**: Mede o poder da questão de diferenciar estudantes com diferentes proficiências.
2. **Parâmetro $b$ (Dificuldade)**: Barra bidirecional (azul para itens fáceis com $b < 0$ e vermelha para complexos com $b > 0$).
3. **Parâmetro $c$ (Chute)**: Gráfico de probabilidade do acerto casual por palpite (chute).

### 🤖 Assistente Pedagógico de IA (Gemini 2.5 Flash)
* Integração direta com a API REST oficial do Gemini para fornecer feedback pedagógico instantâneo.
* **Análise de Erro**: Explica a "pegadinha" ou a lógica incorreta caso o estudante erre a alternativa.
* **Gabarito Justificado**: Destrincha o porquê de a resposta correta ser a verdadeira e por que as outras 4 são distratores.
* **Resumo Teórico**: Apresenta uma breve revisão conceitual do assunto cobrado na questão.

### 🖼️ Pipeline de Recorte Dinâmico de Imagens (PyMuPDF)
* **Detecção Dinâmica de Coluna**: Identifica se a questão é em coluna simples ou de largura inteira (*full-width*) para evitar cortar tabelas e gráficos pela metade.
* **Limite Superior/Inferior Inteligente**: Ignora bordas de cabeçalho azuis e bullet dots decorativos, e delimita o fim do corte baseado na coordenada da alternativa A ou cabeçalho da próxima questão.
* **Recuperação de Fontes Corrompidas**: Compara as palavras extraídas com a base de segurança via taxa de sobreposição lexicográfica para detectar páginas com tabelas de fontes `/ToUnicode` corrompidas, aplicando reversão de texto de segurança contra caracteres fantasma (`™`).

---

## 📂 Estrutura de Pastas

```
enem-pipeline/
├── data/                 # Diretorizados de dados (Parquet TRI e imagens)
│   ├── extracted/        # Imagens finais recortadas das questões (agrupadas por ano)
│   └── fused/            # Arquivos JSONL fundidos unificados (LLM + TRI)
├── scripts/              # Scripts do pipeline de extração e tratamento
│   ├── crop_and_link_images.py   # Algoritmo de visão e recorte do PDF
│   ├── deduplicate_db.py         # Remove cópias de questões entre cores de prova
│   ├── restore_poem_newlines.py  # Reconstrói quebras de linha em poemas
│   └── load_arangodb.py          # Carrega JSONLs para o banco de dados
├── web/                  # Aplicação Web (Node.js/Express + Frontend)
│   ├── public/           # Frontend Estático (HTML, CSS, JS)
│   │   ├── app.js        # Lógica de interatividade e marcações
│   │   ├── index.html    # Estrutura do portal do simulador
│   │   └── style.css     # Estilos visuais e transições
│   └── server.js         # API REST Express e integração Gemini
└── README.md             # Documentação do repositório
```

---

## ⚙️ Instalação e Execução

### Pré-requisitos
* Node.js v18 ou superior.
* Python 3.10 ou superior.
* Banco de dados **ArangoDB** instalado e rodando localmente na porta `8529`.

### 1. Configurando o Servidor Backend (Node.js)
Navegue até a pasta `web/` e instale as dependências:
```bash
cd web
npm install
```

Crie o arquivo `.env` na raiz da pasta `web/` (ou copie do `.env.example` do projeto):
```env
PORT=3000
GEMINI_API_KEY=Sua_Chave_Privada_Gemini_Aqui
ARANGO_HOST=http://localhost:8529
DB_NAME=enem
```

Inicie o servidor local:
```bash
npm start
```
O simulador estará rodando em: `http://localhost:3000`

---

## 🧪 Contribuindo ou Re-processando o Pipeline

Se você deseja rodar novamente o pipeline de recorte de imagens ou deduplicação de banco de dados:

1. Ative o ambiente virtual python:
```bash
source .venv/bin/env
```
2. Para re-recortar as imagens dos cadernos com precisão máxima:
```bash
python3 scripts/crop_and_link_images.py --force
```
3. Para re-executar a deduplicação de questões e limpeza de duplicados no banco de dados:
```bash
python3 scripts/deduplicate_db.py
```
