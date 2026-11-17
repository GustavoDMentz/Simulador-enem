const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { render } = require('../public/markdown-lite');
const { buildExplainRequest, visualContext, SYSTEM } = require('../explain-prompt');
const published = require('../published-questions').load();
const { presentation } = require('../question-presentation');

test('negrito no meio da frase continua em linha e títulos viram h4', () => {
  const html = render('## Análise da escolha\nVocê **acertou** a questão.\n\n**Resumo**\ntexto');
  assert.equal(html, '<h4>Análise da escolha</h4><p>Você <strong>acertou</strong> a questão.</p><h4>Resumo</h4><p>texto</p>');
});

test('listas, itálico e tabela simples', () => {
  const html = render('- **A)** certa\n- **B)** errada\n\n1. um\n2. dois\n\n| a | b |\n|---|---|\n| 1 | 2 |');
  assert.match(html, /<ul><li><strong>A\)<\/strong> certa<\/li><li><strong>B\)<\/strong> errada<\/li><\/ul>/);
  assert.match(html, /<ol><li>um<\/li><li>dois<\/li><\/ol>/);
  assert.match(html, /<table><thead><tr><th>a<\/th><th>b<\/th><\/tr><\/thead><tbody><tr><td>1<\/td><td>2<\/td><\/tr><\/tbody><\/table>/);
});

test('todo HTML vindo da IA é escapado', () => {
  const html = render('<img src=x onerror=alert(1)>\n- <script>x</script>\n## <b>t</b>');
  assert.ok(!/<img|<script|<b>/.test(html));
  assert.match(html, /&lt;img/);
});

test('LaTeX comum vira texto legível, sem confundir "R$ 5"', () => {
  assert.match(render('$x^{2}$ e $\\frac{1}{4}$ e 3 \\times 12'), /x² e 1\/4 e 3 × 12/);
  assert.match(render('Custa R$ 5 e R$ 6.'), /R\$ 5 e R\$ 6\./);
  assert.match(render('$$\\text{Total} = 15\\%$$'), /Total = 15%/);
});

test('a instrução fixa o formato, a fidelidade e proíbe LaTeX', () => {
  for (const must of ['## Análise da escolha do estudante', '## Análise das alternativas', '## Resumo teórico do assunto', 'gabarito oficial', 'Nada de LaTeX', 'No máximo 300 palavras'])
    assert.ok(SYSTEM.includes(must), must);
});

test('o pedido leva a questão, o gabarito, a resposta e a descrição da figura revisada', () => {
  const q = published.find(item => { const d = presentation(item); return d && /Figura: /.test(d.alt || ''); });
  assert.ok(q, 'deveria haver ao menos uma questão publicada com figura descrita');
  const alt = presentation(q).alt;
  const wrong = 'ABCDE'.replace(q.gabarito_oficial, '')[0];
  const body = buildExplainRequest(q, wrong, alt);
  const user = body.contents[0].parts[0].text;
  assert.match(user, new RegExp(`Gabarito oficial: ${q.gabarito_oficial}`));
  assert.match(user, new RegExp(`Resposta do estudante: ${wrong} \\(errou\\)`));
  assert.match(user, /Conteúdo visual descrito por revisores:\nFigura: /);
  assert.ok(!/TRI|parametros/i.test(user));
  assert.equal(body.systemInstruction.parts[0].text, SYSTEM);
  assert.equal(buildExplainRequest(q, undefined, alt).contents[0].parts[0].text.includes('não respondeu'), true);
});

test('visualContext extrai só figura e alternativas em imagem, sem repetir o texto-base', () => {
  const alt = 'Questão 1 do ENEM 2020, dia 1, Matemática. Reprodução do caderno oficial com comando e alternativas A a E. Figura: um gráfico de barras. O comando e as alternativas também estão disponíveis em texto fora da imagem. As alternativas aparecem na imagem e são, em ordem: A) 1; B) 2; C) 3; D) 4; E) 5. Texto-base: muito longo';
  assert.equal(visualContext(alt), 'Figura: um gráfico de barras.\nAs alternativas aparecem na imagem e são, em ordem: A) 1; B) 2; C) 3; D) 4; E) 5.');
  assert.equal(visualContext(undefined), '');
});

test('o servidor envia ao Google a instrução e a mensagem montadas, no formato REST', async () => {
  const app = require('../server');
  const q = published.find(item => item.scoring_enabled === true);
  const realFetch = global.fetch;
  let sent;
  global.fetch = async (url, opts) => { sent = { url, body: JSON.parse(opts.body) }; return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: '## ok' }] } }] }) }; };
  const server = app.listen(0);
  try {
    const { port } = server.address();
    const r = await new Promise((resolve, reject) => {
      const req = http.request({ port, path: `/api/questions/${q.id_unico_sistema}/explain`, method: 'POST', headers: { 'content-type': 'application/json', 'x-gemini-key': 'AQ.Ab8RN6Jexemplo-1234567890_abcdefghij' } },
        res => { let b = ''; res.on('data', c => b += c); res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(b) })); });
      req.on('error', reject);
      req.end(JSON.stringify({ selected: 'A', model: 'gemini-4-hydrogen' }));
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.explanation, '## ok');
    assert.match(sent.url, /models\/gemini-4-hydrogen:generateContent$/);
    assert.ok(sent.body.systemInstruction.parts[0].text.includes('## Resumo teórico do assunto'));
    assert.match(sent.body.contents[0].parts[0].text, new RegExp(`Gabarito oficial: ${q.gabarito_oficial}`));
  } finally { global.fetch = realFetch; server.close(); }
});
