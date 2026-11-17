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
