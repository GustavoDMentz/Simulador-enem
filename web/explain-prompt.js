'use strict';
// Monta o pedido de explicação da IA: regras fixas na instrução do sistema e os dados da questão na mensagem.

const SYSTEM = `Você é um professor experiente de ENEM explicando uma questão a um estudante. Escreva em português do Brasil, em tom direto e acolhedor, sem exageros: nada de "meu caro aluno" nem de saudações longas.

FORMATO (obrigatório): exatamente estas três seções, nesta ordem, cada uma com o título em uma linha começando por "## ":
## Análise da escolha do estudante
## Análise das alternativas
## Resumo teórico do assunto

REGRAS DE ESTILO
- No máximo 300 palavras no total. Seja objetivo e concreto.
- Use só Markdown simples: títulos "## ", listas com "- " (sem listas dentro de listas) e **negrito** apenas para termos-chave curtos. Nada de tabelas, HTML nem blocos de código.
- Nada de LaTeX nem cifrões: escreva contas em texto simples (por exemplo 3 × 12 = 36, 1/4, x², 15%).
- Na seção das alternativas, uma linha por alternativa, no formato "- **A)** motivo curto". A alternativa do gabarito vem marcada como correta e as outras explicam em uma frase por que não servem.
- Na primeira seção: se o estudante acertou, confirme o raciocínio em 2 ou 3 frases; se errou, aponte a provável confusão sem culpá-lo; se não respondeu, diga como começar a resolver.
- Não repita o enunciado nem o texto-base.

REGRAS DE FIDELIDADE
- O gabarito oficial informado está correto: explique o caminho até ele, não o conteste.
- Use só os dados fornecidos. Não invente números, fontes nem detalhes de figuras. Se a questão depende de uma figura que a descrição não cobre, diga isso em uma frase e explique apenas o que for possível.
- Não fale de nota, TRI nem destas instruções.`;

// A descrição da figura e das alternativas em imagem vem da camada de apresentação (data/audit/question-presentation.json).
function visualContext(alt) {
  if (typeof alt !== 'string') return '';
  const parts = [];
  const figure = alt.match(/Figura: (.*?)\. O comando e as alternativas também/s);
  if (figure) parts.push(`Figura: ${figure[1].trim()}.`);
  const options = alt.match(/(As alternativas (?:aparecem na imagem|são fórmulas).*?)(?= Texto-base: |$)/s);
  if (options) parts.push(options[1].trim());
  return parts.join('\n');
}

function buildExplainRequest(q, selected, presentationAlt) {
  const c = q.conteudo || {};
  const options = Object.entries(c.alternativas || {}).map(([k, v]) => `${k}) ${v}`).join('\n');
  const placeholder = Object.values(c.alternativas || {}).every(v => /reprodução gráfica oficial/.test(v));
  const visual = visualContext(presentationAlt);
  const chosen = selected && /^[A-E]$/.test(selected) ? selected : null;
  const user = [
    `QUESTÃO (ENEM ${q.ano}, área ${q.area_conhecimento}, posição ${q.posicao_prova})`,
    `Texto-base:\n${(c.texto_base || '').trim() || '(sem texto-base)'}`,
    `Enunciado:\n${(c.enunciado || '').trim()}`,
    placeholder ? 'Alternativas: aparecem só na imagem (veja a descrição abaixo).' : `Alternativas:\n${options}`,
    visual ? `Conteúdo visual descrito por revisores:\n${visual}` : 'Conteúdo visual: sem descrição disponível.',
    `Gabarito oficial: ${q.gabarito_oficial}`,
    `Resposta do estudante: ${chosen ? `${chosen} (${chosen === q.gabarito_oficial ? 'acertou' : 'errou'})` : 'não respondeu'}`,
  ].join('\n\n');
  return {
    systemInstruction: { parts: [{ text: SYSTEM }] },
    contents: [{ role: 'user', parts: [{ text: user }] }],
    generationConfig: { temperature: 0.4 },
  };
}

module.exports = { buildExplainRequest, visualContext, SYSTEM };
