const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const {scorable}=require('./audit-gate');

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
app.use('/api/published', require('./published-questions').publishedRouter(express));
// Existing simulator endpoints now select the approved isolated release.
app.use('/api', require('./published-questions').publishedRouter(express));

// Servir frontend static files
app.use(express.static(path.join(__dirname, 'public')));

// Servir imagens recortadas do diretório pipeline data
app.use('/images', express.static(path.resolve(__dirname, '../data/extracted')));

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
// Mensagem de erro do Google, curta e sem a chave, para o estudante entender o que houve.
function upstreamMessage(errText, apiKey) {
  let msg = '';
  try { msg = JSON.parse(errText)?.error?.message || ''; } catch { msg = ''; }
  msg = (msg || errText || 'sem detalhes').split(apiKey).join('[chave]').replace(/\s+/g, ' ').trim();
  return msg.length > 300 ? msg.slice(0, 297) + '…' : msg;
}

// Chave BYOK: ausente -> null; com formato aceitável -> a chave; fora do formato -> false.
function geminiKeyFromHeader(value) {
  if (value === undefined || value === null || String(value).trim() === '') return null;
  const key = String(value).trim();
  return /^[A-Za-z0-9_.-]{20,256}$/.test(key) ? key : false;
}

// Modelos: o padrão é configurável (GEMINI_MODEL); o estudante pode escolher outro, validado pelo formato do id.
const DEFAULT_GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-4-hydrogen';
const GEMINI_MODEL_ID = /^gemini-[a-z0-9][a-z0-9.-]{1,60}$/;
const GEMINI_MODEL_SKIP = /(tts|image|live|audio|embedding|robotics|computer-use|aqa|veo|imagen|vision|transcribe|omni|decision|nano-banana|translate)/;

// Transforma a resposta do ListModels do Google em uma lista curta de modelos de texto, os mais novos primeiro.
function pickGeminiModels(apiList) {
  const versionOf = id => parseFloat((id.match(/^gemini-(\d+(?:\.\d+)?)/) || [])[1]) || 0;
  // mais capaz primeiro dentro da mesma versão: Gemini 4 (carbon > argon > hydrogen) e a família pro > flash > lite
  const tier = id => (/carbon|pro/.test(id) ? 0 : /argon/.test(id) ? 1 : /lite/.test(id) ? 4 : /hydrogen/.test(id) ? 3 : 2);
  const seen = new Set();
  return (apiList || [])
    .filter(m => (m.supportedGenerationMethods || []).includes('generateContent'))
    .map(m => ({ id: String(m.name || '').replace(/^models\//, ''), label: m.displayName || '' }))
    .filter(m => GEMINI_MODEL_ID.test(m.id) && !GEMINI_MODEL_SKIP.test(m.id) && !seen.has(m.id) && seen.add(m.id))
    .sort((a, b) => versionOf(b.id) - versionOf(a.id) || tier(a.id) - tier(b.id) || a.id.localeCompare(b.id));
}

// API: modelos Gemini disponíveis para a chave do estudante (a lista do próprio Google, sempre atual)
app.get('/api/gemini/models', async (req, res) => {
  try {
    const userKey = geminiKeyFromHeader(req.get('x-gemini-key'));
    if (userKey === false) return res.status(400).json({ code: 'GEMINI_KEY_INVALID', error: 'A chave informada não tem o formato de uma chave de API do Gemini.' });
    const apiKey = userKey || process.env.GEMINI_API_KEY;
    if (!apiKey) return res.status(401).json({ code: 'GEMINI_KEY_MISSING', error: 'Informe sua chave de API do Gemini para listar os modelos.' });
    const r = await fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000', { headers: { 'x-goog-api-key': apiKey } });
    if (!r.ok) {
      if ([400, 401, 403].includes(r.status)) return res.status(401).json({ code: 'GEMINI_KEY_INVALID', error: 'O Google recusou a chave de API. Confira se ela foi copiada inteira e se está ativa.' });
      return res.status(502).json({ error: 'Não foi possível listar os modelos do Gemini agora.' });
    }
    const data = await r.json();
    res.json({ default: DEFAULT_GEMINI_MODEL, models: pickGeminiModels(data.models) });
  } catch (err) {
    console.error('Erro ao listar modelos do Gemini:', err.message);
    res.status(502).json({ error: 'Não foi possível listar os modelos do Gemini agora.' });
  }
});

// API: Explicar questão por IA (Gemini)
app.post('/api/questions/:id/explain', async (req, res) => {
  try {
    const { selected } = req.body;
    const requestedModel = req.body.model === undefined || req.body.model === '' ? DEFAULT_GEMINI_MODEL : String(req.body.model);
    if (!GEMINI_MODEL_ID.test(requestedModel)) return res.status(400).json({ code: 'GEMINI_MODEL_INVALID', error: 'Modelo do Gemini inválido. Escolha um da lista.' });
    // BYOK: a chave do próprio estudante (cabeçalho) tem prioridade; a do servidor é só um padrão opcional.
    // A chave nunca é registrada em log nem devolvida ao cliente.
    const userKey = geminiKeyFromHeader(req.get('x-gemini-key'));
    if (userKey === false) return res.status(400).json({ code: 'GEMINI_KEY_INVALID', error: 'A chave informada não tem o formato de uma chave de API do Gemini.' });
    const apiKey = userKey || process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(401).json({ code: 'GEMINI_KEY_MISSING', error: 'Informe sua chave de API do Gemini para gerar a explicação.' });
    }
    
    // Read exclusively from the audited, published release; no ArangoDB dependency.
    const published = require('./published-questions').load();
    if (!published) return res.status(503).json({ error: 'Catálogo auditado indisponível.' });
    const q = published.find(item => item._key === req.params.id || item.id_unico_sistema === req.params.id);
    if (!q) return res.status(404).json({ error: 'Questão não encontrada no catálogo publicado.' });
    if (q.scoring_enabled !== true) return res.status(409).json({ error: 'Questão não aprovada.' });

    // 2. Prepara o pedido: regras fixas na instrução do sistema; dados da questão (com a descrição das figuras) na mensagem
    const display = require('./question-presentation').presentation(q);
    const geminiBody = require('./explain-prompt').buildExplainRequest(q, selected, display && display.alt);

    // 3. Chama a API REST do Gemini
    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${requestedModel}:generateContent`;
    const geminiRes = await fetch(geminiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
      body: JSON.stringify(geminiBody)
    });
    
    if (!geminiRes.ok) {
      const errText = await geminiRes.text();
      console.error('Gemini API status:', geminiRes.status, errText.slice(0, 300).split(apiKey).join('[chave]'));
      if ([400, 401, 403].includes(geminiRes.status) && /API key|API_KEY|PERMISSION_DENIED|UNAUTHENTICATED/i.test(errText)) {
        return res.status(401).json({ code: 'GEMINI_KEY_INVALID', error: 'O Google recusou a chave de API. Confira se ela foi copiada inteira e se está ativa.' });
      }
      if (geminiRes.status === 404) {
        return res.status(404).json({ code: 'GEMINI_MODEL_INVALID', error: 'O Google não encontrou esse modelo para a sua chave. Escolha outro na lista de modelos.' });
      }
      if (geminiRes.status === 429) {
        return res.status(429).json({ code: 'GEMINI_QUOTA', error: 'A cota gratuita da sua chave acabou por agora. Tente novamente em alguns minutos.' });
      }
      if (geminiRes.status === 503 || geminiRes.status === 500) {
        return res.status(502).json({ code: 'GEMINI_BUSY', error: `O Google está sobrecarregado com o modelo ${requestedModel} (HTTP ${geminiRes.status}). Tente de novo em instantes ou escolha outro modelo.` });
      }
      return res.status(502).json({ code: 'GEMINI_UPSTREAM', error: `O Google recusou o pedido com o modelo ${requestedModel} (HTTP ${geminiRes.status}): ${upstreamMessage(errText, apiKey)}` });
    }
    
    const geminiData = await geminiRes.json();
    const explanation = geminiData.candidates?.[0]?.content?.parts?.[0]?.text || "Não foi possível gerar a explicação.";
    
    res.json({ explanation });
  } catch (err) {
    console.error("Erro ao gerar explicação por IA:", err);
    res.status(500).json({ error: 'Falha interna ao gerar explicação.' });
  }
});

if (require.main === module) app.listen(PORT, () => {
  console.log(`============================================================`);
  console.log(`🚀 Simulador ENEM ativo em http://localhost:${PORT}`);
  console.log(`============================================================`);
});

module.exports = app;
module.exports.geminiKeyFromHeader = geminiKeyFromHeader;
module.exports.pickGeminiModels = pickGeminiModels;
