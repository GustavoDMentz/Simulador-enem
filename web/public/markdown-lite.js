// Renderizador de Markdown mínimo e seguro para a explicação da IA: títulos, listas, tabelas simples,
// negrito/itálico/código e limpeza de LaTeX comum. Todo o texto é escapado antes de virar HTML.
(function (root) {
  'use strict';
  const SUP = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻', n: 'ⁿ' };
  const SUB = { '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉' };
  const mapChars = (text, table) => [...text].every(c => table[c]) ? [...text].map(c => table[c]).join('') : null;

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function latex(s) {
    let t = s;
    t = t.replace(/(?<![\w\\])\$\$?(?!\s)([^$\n]+?)(?<!\s)\$\$?(?!\d)/g, '$1'); // $x$ e $$x$$ (sem tocar em "R$ 5")
    t = t.replace(/\\\(|\\\)|\\\[|\\\]/g, '');
    for (let i = 0; i < 3; i++) {
      t = t.replace(/\\(?:text|mathrm|mathbf|textbf|operatorname)\{([^{}]*)\}/g, '$1');
      t = t.replace(/\\frac\{([^{}]*)\}\{([^{}]*)\}/g, (_, a, b) => (/^\w+$/.test(a) && /^\w+$/.test(b) ? `${a}/${b}` : `(${a})/(${b})`));
      t = t.replace(/\\sqrt\{([^{}]*)\}/g, '√($1)');
    }
    const words = { times: '×', cdot: '·', div: '÷', approx: '≈', leq: '≤', le: '≤', geq: '≥', ge: '≥', neq: '≠', circ: '°', pi: 'π', Delta: 'Δ', delta: 'δ', alpha: 'α', beta: 'β', theta: 'θ', mu: 'μ', rightarrow: '→', to: '→', pm: '±', infty: '∞' };
    t = t.replace(/\\([A-Za-z]+)/g, (m, w) => (w in words ? words[w] : m));
    t = t.replace(/\\left|\\right|\\[,;:! ]/g, '').replace(/\\%/g, '%');
    t = t.replace(/\^\{([^{}]*)\}/g, (m, x) => mapChars(x, SUP) || `^(${x})`).replace(/\^([0-9n])/g, (m, x) => SUP[x]);
    t = t.replace(/_\{([0-9]+)\}/g, (m, x) => mapChars(x, SUB) || m).replace(/(?<=[A-Za-z])_([0-9])/g, (m, x) => SUB[x]);
    return t;
  }

  function inline(s) {
    return s
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>')
      .replace(/(^|[\s(])_([^_\s][^_]*?)_(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>');
  }

  function cells(row) {
    return row.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
  }

  function render(md) {
    const lines = latex(String(md == null ? '' : md)).replace(/\r/g, '').split('\n');
    const out = [];
    let para = [], list = null, table = [];
    const flushPara = () => { if (para.length) out.push(`<p>${para.join('<br>')}</p>`); para = []; };
    const flushList = () => { if (list) out.push(`<${list.tag}>${list.items.map(i => `<li>${i}</li>`).join('')}</${list.tag}>`); list = null; };
    const flushTable = () => {
      if (!table.length) return;
      const rows = table.filter(r => !/^\|?[\s:|-]+\|?$/.test(r)).map(cells);
      if (rows.length) {
        const [head, ...body] = rows;
        out.push('<div class="md-table-wrap"><table><thead><tr>' + head.map(c => `<th>${inline(esc(c))}</th>`).join('') + '</tr></thead><tbody>' +
          body.map(r => '<tr>' + r.map(c => `<td>${inline(esc(c))}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>');
      }
      table = [];
    };
    const flushAll = () => { flushPara(); flushList(); flushTable(); };

    for (const raw of lines) {
      const t = raw.trim();
      if (!t) { flushAll(); continue; }
      if (t.startsWith('|')) { flushPara(); flushList(); table.push(t); continue; }
      flushTable();
      if (/^(-{3,}|\*{3,}|_{3,})$/.test(t)) { flushAll(); continue; }
      const text = esc(t);
      let m;
      if ((m = text.match(/^#{1,6}\s+(.*?)\s*#*$/))) { flushAll(); out.push(`<h4>${inline(m[1].replace(/^\*\*(.*)\*\*$/, '$1'))}</h4>`); continue; }
      if ((m = text.match(/^\*\*([^*]{1,80}?)\*\*:?$/))) { flushAll(); out.push(`<h4>${inline(m[1])}</h4>`); continue; }
      if ((m = text.match(/^[-*•]\s+(.*)$/))) { flushPara(); if (!list || list.tag !== 'ul') { flushList(); list = { tag: 'ul', items: [] }; } list.items.push(inline(m[1])); continue; }
      if ((m = text.match(/^\d+[.)]\s+(.*)$/))) { flushPara(); if (!list || list.tag !== 'ol') { flushList(); list = { tag: 'ol', items: [] }; } list.items.push(inline(m[1])); continue; }
      flushList();
      para.push(inline(text));
    }
    flushAll();
    return out.join('');
  }

  const api = { render, latex };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.MarkdownLite = api;
})(typeof window !== 'undefined' ? window : globalThis);
