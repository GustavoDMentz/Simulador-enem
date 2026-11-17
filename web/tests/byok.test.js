const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');

delete process.env.GEMINI_API_KEY;
const app = require('../server');

function post(server, path, headers = {}) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    const req = http.request({ port, path, method: 'POST', headers: { 'content-type': 'application/json', ...headers } }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(body) }));
    });
    req.on('error', reject);
    req.end(JSON.stringify({ selected: 'A' }));
  });
}

test('geminiKeyFromHeader: ausente é null, formato válido passa, lixo é recusado', () => {
  const f = app.geminiKeyFromHeader;
  assert.equal(f(undefined), null);
  assert.equal(f('   '), null);
  assert.equal(f(' AIzaSyA-1234567890_abcdefghijklmnop '), 'AIzaSyA-1234567890_abcdefghijklmnop');
  assert.equal(f('AQ.Ab8RN6Jexemplo-1234567890_abcdefghij'), 'AQ.Ab8RN6Jexemplo-1234567890_abcdefghij'); // formato novo, com ponto
  assert.equal(f('curta'), false);
  assert.equal(f('AIzaSyA 1234567890 abcdefghijklmnop'), false);
  assert.equal(f('AIza\r\nX-Injetado: 1234567890abcdef'), false);
});

test('explain sem chave (do usuário ou do servidor) pede a chave, com código estável', async () => {
  const server = app.listen(0);
  try {
    const r = await post(server, '/api/questions/qualquer/explain');
    assert.equal(r.status, 401);
    assert.equal(r.body.code, 'GEMINI_KEY_MISSING');
    assert.match(r.body.error, /chave de API do Gemini/i);
  } finally { server.close(); }
});

test('explain com chave malformada é recusado antes de qualquer chamada externa', async () => {
  const server = app.listen(0);
  try {
    const r = await post(server, '/api/questions/qualquer/explain', { 'x-gemini-key': 'nao é uma chave' });
    assert.equal(r.status, 400);
    assert.equal(r.body.code, 'GEMINI_KEY_INVALID');
  } finally { server.close(); }
});

test('pickGeminiModels: só modelos de texto com generateContent, mais novos primeiro, sem duplicados', () => {
  const m = (name, methods = ['generateContent']) => ({ name: `models/${name}`, supportedGenerationMethods: methods });
  const out = app.pickGeminiModels([
    m('gemini-3.8-flash'), m('gemini-4-hydrogen'), m('gemini-4-carbon'), m('gemini-4-argon'), m('gemini-3.5-flash-lite'), m('gemini-3.1-pro-preview'), m('gemini-4-hydrogen'),
    m('gemini-embedding-001', ['embedContent']), m('gemini-3.8-flash-tts'), m('gemini-3.8-live'), m('gemini-3.1-flash-image'), m('gemini-omni-1.2-flash'), m('text-bison-001'),
  ]).map(x => x.id);
  assert.deepEqual(out, ['gemini-4-carbon', 'gemini-4-argon', 'gemini-4-hydrogen', 'gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-3.1-pro-preview']);
});

test('explain recusa id de modelo malformado antes de chamar o Google', async () => {
  const server = app.listen(0);
  try {
    const { port } = server.address();
    const r = await new Promise((resolve, reject) => {
      const req = http.request({ port, path: '/api/questions/q/explain', method: 'POST', headers: { 'content-type': 'application/json', 'x-gemini-key': 'AQ.Ab8RN6Jexemplo-1234567890_abcdefghij' } },
        res => { let b = ''; res.on('data', c => b += c); res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(b) })); });
      req.on('error', reject);
      req.end(JSON.stringify({ selected: 'A', model: '../../v1/outro?x=1' }));
    });
    assert.equal(r.status, 400);
    assert.equal(r.body.code, 'GEMINI_MODEL_INVALID');
  } finally { server.close(); }
});

test('GET /api/gemini/models sem chave pede a chave', async () => {
  const server = app.listen(0);
  try {
    const { port } = server.address();
    const r = await new Promise((resolve, reject) => http.get({ port, path: '/api/gemini/models' }, res => { let b = ''; res.on('data', c => b += c); res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(b) })); }).on('error', reject));
    assert.equal(r.status, 401);
    assert.equal(r.body.code, 'GEMINI_KEY_MISSING');
  } finally { server.close(); }
});

test('erro do Google que não é de chave/cota/modelo mostra o status e a mensagem, sem vazar a chave', async () => {
  const key = 'AQ.Ab8RN6Jexemplo-1234567890_abcdefghij';
  const realFetch = global.fetch;
  global.fetch = async () => ({ ok: false, status: 400, text: async () => JSON.stringify({ error: { message: `Thinking level not supported for this model. key=${key}` } }) });
  const server = app.listen(0);
  try {
    const { port } = server.address();
    const r = await new Promise((resolve, reject) => {
      const req = http.request({ port, path: '/api/questions/2024_AZUL_D2_Q153/explain', method: 'POST', headers: { 'content-type': 'application/json', 'x-gemini-key': key } },
        res => { let b = ''; res.on('data', c => b += c); res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(b) })); });
      req.on('error', reject);
      req.end(JSON.stringify({ selected: 'A', model: 'gemini-3.5-flash-lite' }));
    });
    assert.equal(r.status, 502);
    assert.equal(r.body.code, 'GEMINI_UPSTREAM');
    assert.match(r.body.error, /gemini-3\.5-flash-lite/);
    assert.match(r.body.error, /HTTP 400/);
    assert.match(r.body.error, /Thinking level not supported/);
    assert.ok(!r.body.error.includes(key));
  } finally { global.fetch = realFetch; server.close(); }
});
