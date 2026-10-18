const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// Parse .env from parent directory (explicit environment variables take precedence)
const dotenvPath = path.join(__dirname, '../.env');
if (fs.existsSync(dotenvPath)) {
  const envContent = fs.readFileSync(dotenvPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const parts = line.split('=');
    if (parts.length >= 2) {
      const key = parts[0].trim();
      const val = parts.slice(1).join('=').trim();
      if (key && process.env[key] === undefined) process.env[key] = val;
    }
  });
}

const ARANGO_HOST = (process.env.ARANGO_HOST || 'http://127.0.0.1:8529').replace(/\/$/, '');
const DB_NAME = process.env.ARANGO_DB || 'enem';
const ARANGO_USER = process.env.ARANGO_USER || 'root';
const ARANGO_PASSWORD = process.env.ARANGO_PASSWORD;

app.use(express.json());

// Isolated audited-question API; existing ArangoDB endpoints remain unchanged.
app.use('/api/audit', require('./audit-gate').auditRouter(express));

// Servir frontend static files
app.use(express.static(path.join(__dirname, 'public')));

// Servir imagens recortadas do diretório pipeline data
app.use('/images', express.static('/home/gumentz/enem-pipeline/data/extracted'));

// Helper para se comunicar com o ArangoDB HTTP API
async function arangoQuery(query, bindVars = {}) {
  if (ARANGO_PASSWORD === undefined) {
    throw new Error('ARANGO_PASSWORD não configurada. Defina a variável de ambiente antes de iniciar o servidor.');
  }
  const url = `${ARANGO_HOST}/_db/${encodeURIComponent(DB_NAME)}/_api/cursor`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Basic ' + Buffer.from(`${ARANGO_USER}:${ARANGO_PASSWORD}`).toString('base64')
    },
    body: JSON.stringify({ query, bindVars })
  });
  
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`ArangoDB Error: ${errText}`);
  }
  
  const data = await response.json();
  return data.result;
}

function formatQuestion(q) {
  if (!q) return q;

  // 1. Reescrever caminhos de imagem
  if (q.conteudo && q.conteudo.metadados_visual && q.conteudo.metadados_visual.caminho_local_imagem) {
    const absPath = q.conteudo.metadados_visual.caminho_local_imagem;
    // Traduz '/home/gumentz/enem-pipeline/data/extracted/2025/images/...' para '/images/2025/images/...'
    const relPath = absPath.replace("/home/gumentz/enem-pipeline/data/extracted/", "/images/");
    q.conteudo.metadados_visual.caminho_local_imagem = relPath;
  }

  // 2. Limpar enunciados que repetem o texto_base no início
  if (q.conteudo && q.conteudo.texto_base && q.conteudo.enunciado) {
    let base = q.conteudo.texto_base.trim();
    let enun = q.conteudo.enunciado.trim();

    if (enun.startsWith(base)) {
      q.conteudo.enunciado = enun.substring(base.length).trim();
    } else {
      // Fallback de normalização de espaços (para lidar com pequenas discrepâncias de quebra de linha)
      const normBase = base.replace(/\s+/g, ' ');
      const normEnun = enun.replace(/\s+/g, ' ');
      if (normEnun.startsWith(normBase)) {
        let suffixNorm = normEnun.substring(normBase.length).trim();
        let searchSnippet = suffixNorm.substring(0, 15);
        let idx = enun.indexOf(searchSnippet);
        if (idx !== -1) {
          q.conteudo.enunciado = enun.substring(idx).trim();
        }
      }
    }
  }

  return q;
}

// API: Buscar metadados para preencher filtros
app.get('/api/metadata', async (req, res) => {
  try {
    const query = `
      RETURN {
        anos: (FOR q IN Questoes COLLECT ano = q.ano RETURN ano),
        areas: (FOR q IN Questoes COLLECT area = q.area_conhecimento RETURN area),
        dias: (FOR q IN Questoes COLLECT dia = q.dia RETURN dia)
      }
    `;
    const result = await arangoQuery(query);
    res.json(result[0] || { anos: [], areas: [], dias: [] });
  } catch (err) {
    console.error("Erro ao buscar metadados:", err);
    res.status(500).json({ error: err.message });
  }
});

// API: Listar questões filtradas
app.get('/api/questions', async (req, res) => {
  try {
    const filters = [];
    const bindVars = {};
    
    if (req.query.year) {
      filters.push("q.ano == @year");
      bindVars.year = parseInt(req.query.year);
    }
    if (req.query.day) {
      filters.push("q.dia == @day");
      bindVars.day = parseInt(req.query.day);
    }
    if (req.query.area) {
      filters.push("q.area_conhecimento == @area");
      bindVars.area = req.query.area;
    }
    if (req.query.has_image === 'true') {
      filters.push("q.conteudo.metadados_visual.caminho_local_imagem != null");
    }
    if (req.query.position) {
      const posVal = parseInt(req.query.position);
      bindVars.position = posVal;
      filters.push("(q.posicao_prova == @position || (q.dia == 2 && q.posicao_prova == @position + 90))");
    }
    
    const filterStr = filters.length > 0 ? "FILTER " + filters.join(" && ") : "";
    
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const offset = (page - 1) * limit;
    
    const countBindVars = { ...bindVars };
    
    bindVars.offset = offset;
    bindVars.limit = limit;
    
    const queryQuestions = `
      FOR q IN Questoes
      ${filterStr}
      SORT q.ano DESC, q.dia ASC, q.posicao_prova ASC
      LIMIT @offset, @limit
      RETURN q
    `;
    
    const queryCount = `
      RETURN LENGTH(
        FOR q IN Questoes
        ${filterStr}
        RETURN 1
      )
    `;
    
    const [questions, countResult] = await Promise.all([
      arangoQuery(queryQuestions, bindVars),
      arangoQuery(queryCount, countBindVars)
    ]);
    
    const total = countResult[0] || 0;
    const formatted = questions.map(formatQuestion);
    
    res.json({
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
      results: formatted
    });
  } catch (err) {
    console.error("Erro ao buscar questões:", err);
    res.status(500).json({ error: err.message });
  }
});

// API: Buscar uma questão aleatória com filtros
app.get('/api/questions/random', async (req, res) => {
  try {
    const filters = [];
    const bindVars = {};
    
    if (req.query.year) {
      filters.push("q.ano == @year");
      bindVars.year = parseInt(req.query.year);
    }
    if (req.query.day) {
      filters.push("q.dia == @day");
      bindVars.day = parseInt(req.query.day);
    }
    if (req.query.area) {
      filters.push("q.area_conhecimento == @area");
      bindVars.area = req.query.area;
    }
    if (req.query.has_image === 'true') {
      filters.push("q.conteudo.metadados_visual.caminho_local_imagem != null");
    }
    if (req.query.position) {
      const posVal = parseInt(req.query.position);
      bindVars.position = posVal;
      filters.push("(q.posicao_prova == @position || (q.dia == 2 && q.posicao_prova == @position + 90))");
    }
    
    const filterStr = filters.length > 0 ? "FILTER " + filters.join(" && ") : "";
    
    const query = `
      FOR q IN Questoes
      ${filterStr}
      SORT RAND()
      LIMIT 1
      RETURN q
    `;
    
    const result = await arangoQuery(query, bindVars);
    if (result.length > 0) {
      res.json(formatQuestion(result[0]));
    } else {
      res.status(404).json({ error: "Nenhuma questão encontrada para os filtros aplicados." });
    }
  } catch (err) {
    console.error("Erro ao buscar questão aleatória:", err);
    res.status(500).json({ error: err.message });
  }
});

// API: Detalhes de uma questão por ID
app.get('/api/questions/:id', async (req, res) => {
  try {
    const query = `
      FOR q IN Questoes
      FILTER q._key == @key
      RETURN q
    `;
    const result = await arangoQuery(query, { key: req.params.id });
    if (result.length > 0) {
      res.json(formatQuestion(result[0]));
    } else {
      res.status(404).json({ error: "Questão não encontrada." });
    }
  } catch (err) {
    console.error("Erro ao buscar questão por ID:", err);
    res.status(500).json({ error: err.message });
  }
});
// API: Explicar questão por IA (Gemini)
app.post('/api/questions/:id/explain', async (req, res) => {
  try {
    const { selected } = req.body;
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: "Chave de API do Gemini não configurada no servidor." });
    }
    
    // 1. Busca os detalhes da questão no banco
    const query = `
      FOR q IN Questoes
      FILTER q._key == @key
      RETURN q
    `;
    const result = await arangoQuery(query, { key: req.params.id });
    if (result.length === 0) {
      return res.status(404).json({ error: "Questão não encontrada." });
    }
    const q = result[0];
    
    // 2. Prepara o prompt para o Gemini
    const enunciado = q.conteudo.enunciado;
    const textoBase = q.conteudo.texto_base || "(Sem texto base)";
    const alternativas = JSON.stringify(q.conteudo.alternativas, null, 2);
    const gabarito = q.gabarito_oficial;
    const tri = q.parametros_tri;
    const descImagem = q.conteudo.metadados_visual.descricao_imagem || "(Sem imagens ou sem descrição)";
    
    const prompt = `
Você é um professor especialista em ENEM. Explique a seguinte questão de forma didática e motivadora.

DADOS DA QUESTÃO:
- ID: ${q._key}
- Ano: ${q.ano}
- Área: ${q.area_conhecimento}
- Texto Base: ${textoBase}
- Enunciado: ${enunciado}
- Alternativas:
${alternativas}
- Gabarito Oficial: ${gabarito}
- Descrição da Imagem de Apoio (se houver): ${descImagem}
- Parâmetros TRI da Questão:
  * Discriminação (a): ${tri.a_discriminacao.toFixed(2)} (Mede a qualidade de diferenciação)
  * Dificuldade (b): ${tri.b_dificuldade.toFixed(2)} (Mede a complexidade da questão)
  * Chute (c): ${(tri.c_chute * 100).toFixed(1)}% (Chance de acerto ao acaso)

RESPOSTA DO ESTUDANTE:
- O estudante escolheu a alternativa: ${selected || "(Não selecionada)"}
- Resultado: ${selected === gabarito ? "ACERTOU!" : "ERROU!"}

INSTRUÇÕES DE FORMATO:
Estruture sua explicação em português usando Markdown limpo com exatamente estes 3 títulos principais em negrito (usando ** no início da linha, NÃO use # ou ##):

**Análise da Escolha do Estudante**
Se o estudante errou (gabarito é ${gabarito} mas ele marcou ${selected}), explique com muita paciência e gentileza por que a alternativa ${selected} está errada e qual foi a provável "pegadinha" ou confusão conceitual que o levou a esse erro. Se ele acertou, parabenize-o e confirme o raciocínio correto.

**Análise das Alternativas**
Explique brevemente, em uma lista com marcadores:
* Por que a alternativa ${gabarito} é a única correta.
* Por que as demais 4 alternativas estão incorretas (mencione-as brevemente).

**Resumo Teórico do Assunto**
Dê um panorama geral sucinto e de alto valor (bullet points ou parágrafo curto) sobre o conceito cobrado nesta questão (seja ele um conceito de Física, História, Matemática, etc.) para ajudar o estudante a fixar o assunto.
`;

    // 3. Chama a API REST do Gemini
    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
    const geminiRes = await fetch(geminiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }]
      })
    });
    
    if (!geminiRes.ok) {
      const errText = await geminiRes.text();
      throw new Error(`Gemini API Error: ${errText}`);
    }
    
    const geminiData = await geminiRes.json();
    const explanation = geminiData.candidates?.[0]?.content?.parts?.[0]?.text || "Não foi possível gerar a explicação.";
    
    res.json({ explanation });
  } catch (err) {
    console.error("Erro ao gerar explicação por IA:", err);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`============================================================`);
  console.log(`🚀 Simulador ENEM ativo em http://localhost:${PORT}`);
  console.log(`============================================================`);
});
