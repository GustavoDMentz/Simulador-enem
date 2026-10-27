// State Management
let activeQuestion = null;
let selectedAlternative = null;
let currentPage = 1;
const limitPerPage = 12;

// Elements
const filterYear = document.getElementById('filter-year');
const filterDay = document.getElementById('filter-day');
const filterArea = document.getElementById('filter-area');
const filterPosition = document.getElementById('filter-position');
const filterImage = document.getElementById('filter-image');
const btnRandom = document.getElementById('btn-random');
const questionsList = document.getElementById('questions-list');
const questionsCount = document.getElementById('questions-count');

const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const pageIndicator = document.getElementById('page-indicator');

// Question Display Elements
const badgeId = document.getElementById('badge-id');
const badgeYear = document.getElementById('badge-year');
const badgeArea = document.getElementById('badge-area');
const badgeColor = document.getElementById('badge-color');

const textBase = document.getElementById('question-text-base');
const imageContainer = document.getElementById('question-image-container');
const questionImg = document.getElementById('question-img');
const btnToggleDesc = document.getElementById('btn-toggle-desc');
const questionDescText = document.getElementById('question-desc-text');
const enunciado = document.getElementById('question-enunciado');
const alternativeCards = document.querySelectorAll('.alternative-card');

const btnSubmit = document.getElementById('btn-submit');
const btnNextQuestion = document.getElementById('btn-next-question');

// TRI Dashboard Elements
const triDashboard = document.getElementById('tri-dashboard');
const answerFeedback = document.getElementById('answer-feedback');
const triValA = document.getElementById('tri-val-a');
const triValB = document.getElementById('tri-val-b');
const triValC = document.getElementById('tri-val-c');
const gaugeBarA = document.getElementById('gauge-bar-a');
const gaugeBarB = document.getElementById('gauge-bar-b');
const gaugeBarC = document.getElementById('gauge-bar-c');

// AI Help Elements
const btnAiExplain = document.getElementById('btn-ai-explain');
const aiExplanationContainer = document.getElementById('ai-explanation-container');
const aiExplanationContent = document.getElementById('ai-explanation-content');

// API Base URLs
const API_URL = '/api';

// Initialize App
async function init() {
  await loadFiltersMetadata();
  setupEventListeners();
  updateQuestionButtonLabel();
  await loadQuestionsList();
  
  // Load a random question to start
  loadRandomQuestion();
}

// 1. Fetch Metadata (years, areas, days) and populate filter dropdowns
async function loadFiltersMetadata() {
  try {
    const res = await fetch(`${API_URL}/metadata`);
    const data = await res.json();
    
    document.getElementById("approved-total").textContent = data.total ?? 0;
    document.getElementById("approved-images").textContent = data.images ?? 0;
    // Populate Years
    if (data.anos) {
      data.anos.sort((a, b) => b - a).forEach(year => {
        const opt = document.createElement('option');
        opt.value = year;
        opt.textContent = year;
        filterYear.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Falha ao carregar metadados dos filtros:", err);
  }
}

// 2. Setup Event Listeners
function setupEventListeners() {
  // Filters
  filterYear.addEventListener('change', resetAndReloadList);
  filterDay.addEventListener('change', resetAndReloadList);
  filterArea.addEventListener('change', resetAndReloadList);
  filterPosition.addEventListener('input', resetAndReloadList);
  filterImage.addEventListener('change', resetAndReloadList);
  
  // Randomizer
  btnRandom.addEventListener('click', loadRandomQuestion);
  
  // Pagination
  btnPrev.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadQuestionsList();
    }
  });
  
  btnNext.addEventListener('click', () => {
    currentPage++;
    loadQuestionsList();
  });
  
  // Alternatives selection
  alternativeCards.forEach(card => {
    card.setAttribute('role','button');
    card.tabIndex = 0;
    card.addEventListener('keydown', e => {
      if(e.target !== card) return;
      if(e.key === 'Enter' || e.key === ' '){e.preventDefault();card.click()}
      if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();const all=[...alternativeCards];all[(all.indexOf(card)+(e.key==='ArrowDown'?1:4))%5].focus()}
    });
    card.addEventListener('click', () => {
      if (card.classList.contains('disabled') || card.classList.contains('eliminated')) return;
      
      // Select clicked card
      alternativeCards.forEach(c => {c.classList.remove('selected');c.setAttribute('aria-pressed','false')});
      card.classList.add('selected');
      card.setAttribute('aria-pressed','true');
      
      selectedAlternative = card.dataset.letter;
      if (activeQuestion?.scoring_enabled === true) btnSubmit.removeAttribute('disabled');
    });
    
    // Scissor / eliminate button click
    const btnEliminate = card.querySelector('.btn-eliminate');
    if (btnEliminate) {
      btnEliminate.addEventListener('click', (e) => {
        e.stopPropagation(); // Avoid choosing alternative
        if (card.classList.contains('disabled')) return;
        
        card.classList.toggle('eliminated');
        // If the card was selected and now gets eliminated, unselect it
        if (card.classList.contains('eliminated') && card.classList.contains('selected')) {
          card.classList.remove('selected');
          selectedAlternative = null;
          btnSubmit.setAttribute('disabled', 'true');
        }
      });
    }
  });
  
  // Answer submission
  btnSubmit.addEventListener('click', submitAnswer);
  
  // Next question navigation
  btnNextQuestion.addEventListener('click', loadNextQuestion);
  
  // Toggle IA Description
  btnToggleDesc.addEventListener('click', () => {toggleIaDescription();btnToggleDesc.setAttribute('aria-expanded',String(!questionDescText.classList.contains('hidden')))});
  document.getElementById('btn-enlarge-image').addEventListener('click', () => openImageViewer(questionImg.src, questionImg.alt));
  document.getElementById('btn-original-source').addEventListener('click', e => openImageViewer(e.currentTarget.dataset.src, 'Reprodução original do material oficial'));
  document.getElementById('btn-close-image').addEventListener('click', closeImageViewer);
  document.getElementById('image-viewer').addEventListener('close', e => {
    // Native close already restores focus. A queued close event must not steal
    // focus after the student has moved on to an answer or another control.
    if(document.activeElement === document.body || e.currentTarget.contains(document.activeElement)) imageTrigger?.focus();
  });
  document.getElementById('image-zoom').addEventListener('change', e => document.getElementById('image-viewer').classList.toggle('original-size', e.target.checked));
  
  // AI Explanation Trigger
  btnAiExplain.addEventListener('click', getAiExplanation);
}

function updateQuestionButtonLabel() {
  const filtered = Boolean(filterYear.value || filterDay.value || filterArea.value || filterPosition.value || filterImage.checked);
  btnRandom.textContent = filtered ? '🎲 Sortear entre as filtradas' : '🎲 Questão Aleatória';
}

function resetAndReloadList() {
  updateQuestionButtonLabel();
  currentPage = 1;
  loadQuestionsList();
}

// 3. Load Questions List based on current filters
async function loadQuestionsList() {
  try {
    questionsList.innerHTML = '<p class="empty-msg">Buscando questões...</p>';
    
    const params = new URLSearchParams({
      page: currentPage,
      limit: limitPerPage
    });
    
    if (filterYear.value) params.append('year', filterYear.value);
    if (filterDay.value) params.append('day', filterDay.value);
    if (filterArea.value) params.append('area', filterArea.value);
    if (filterPosition.value) params.append('position', filterPosition.value);
    if (filterImage.checked) params.append('has_image', 'true');
    
    const res = await fetch(`${API_URL}/questions?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    if (!Array.isArray(data.results)) throw new Error('Resposta de questões inválida');
    
    questionsCount.textContent = data.total;
    questionsList.innerHTML = '';
    
    if (!data.results || data.results.length === 0) {
      questionsList.innerHTML = '<p class="empty-msg">Nenhuma questão encontrada.</p>';
      btnPrev.setAttribute('disabled', 'true');
      btnNext.setAttribute('disabled', 'true');
      pageIndicator.textContent = '1 / 1';
      return;
    }
    
    data.results.forEach(q => {
      const item = document.createElement('div');
      item.classList.add('list-item');
      item.dataset.key = q._key;
      if (activeQuestion && activeQuestion._key === q._key) {
        item.classList.add('active');
      }
      
      // Simple preview title
      const hasImgIndicator = q.conteudo.metadados_visual?.contem_imagem ? '🖼️ ' : '';
      const previewText = q.conteudo.enunciado.substring(0, 45) + '...';
      item.innerHTML = `<strong>Q${q.posicao_prova}</strong> - ${hasImgIndicator}${previewText} <span style="font-size:10px; color:#94a3b8; display:block;">${q.ano} • D${q.dia} • ${q.area_conhecimento}</span>`;
      
      item.addEventListener('click', () => {
        // Remove active class from previous
        document.querySelectorAll('.list-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        displayQuestion(q);
        if (window.matchMedia('(max-width: 900px)').matches) {
          document.querySelector('.content-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
      
      questionsList.appendChild(item);
    });
    
    // Update pagination buttons
    btnPrev.toggleAttribute('disabled', currentPage === 1);
    btnNext.toggleAttribute('disabled', currentPage >= data.totalPages);
    pageIndicator.textContent = `${currentPage} / ${data.totalPages || 1}`;
    
  } catch (err) {
    console.error("Erro ao carregar lista de questões:", err);
    questionsList.innerHTML = '<p class="empty-msg" role="alert">Não foi possível carregar as questões. Tente atualizar a página.</p>';
  }
}

// 4. Load a random question matching filters
async function loadRandomQuestion() {
  try {
    const params = new URLSearchParams();
    if (filterYear.value) params.append('year', filterYear.value);
    if (filterDay.value) params.append('day', filterDay.value);
    if (filterArea.value) params.append('area', filterArea.value);
    if (filterPosition.value) params.append('position', filterPosition.value);
    if (filterImage.checked) params.append('has_image', 'true');
    
    const res = await fetch(`${API_URL}/questions/random?${params.toString()}`);
    if (!res.ok) {
      alert("Nenhuma questão encontrada para os filtros aplicados.");
      return;
    }
    const q = await res.json();
    displayQuestion(q);
    if (window.matchMedia('(max-width: 900px)').matches) {
      document.querySelector('.content-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Highlight in list if present
    document.querySelectorAll('.list-item').forEach(item => {
      if (item.dataset.key === q._key) {
        item.classList.add('active');
        item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else {
        item.classList.remove('active');
      }
    });
  } catch (err) {
    console.error("Falha ao buscar questão aleatória:", err);
  }
}

// 4b. Load the next question sequentially from the active list
function loadNextQuestion() {
  const activeItem = questionsList.querySelector('.list-item.active');
  if (activeItem) {
    const nextItem = activeItem.nextElementSibling;
    if (nextItem) {
      nextItem.click();
      nextItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      return;
    }
  }
  
  // If we reached the end of the page or there is no active item, go to next page
  const nextButtonDisabled = btnNext.hasAttribute('disabled');
  if (!nextButtonDisabled) {
    currentPage++;
    loadQuestionsList().then(() => {
      const firstItem = questionsList.querySelector('.list-item');
      if (firstItem) {
        firstItem.click();
        firstItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    });
  } else {
    // Wrap around to the first page if there are pages, otherwise fallback to random
    const hasItems = questionsList.querySelector('.list-item');
    if (hasItems) {
      currentPage = 1;
      loadQuestionsList().then(() => {
        const firstItem = questionsList.querySelector('.list-item');
        if (firstItem) {
          firstItem.click();
          firstItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
      });
    } else {
      // Fallback: clear search filters and fetch a random question
      if (filterPosition.value) {
        filterPosition.value = "";
      }
      loadRandomQuestion();
    }
  }
}

// 5. Render a question in the main card
function displayQuestion(q) {
  activeQuestion = q;
  selectedAlternative = null;
  
  // Header Badges
  badgeId.textContent = q.id_unico_sistema || q._key;
  badgeYear.textContent = q.ano;
  badgeArea.textContent = q.area_conhecimento;
  badgeColor.textContent = q.cor_prova;
  
  // Set area of knowledge visual style
  badgeArea.className = 'badge badge-gray';
  
  const c = q.conteudo, p = q.presentation;
  const mode = p?.mode || (c.metadados_visual?.caminho_local_imagem ? 'composition' : 'text');
  document.querySelector('.question-card').dataset.presentation = mode;
  const baseText = p?.mode === 'figure' ? p.before : c.texto_base;
  textBase.textContent = p?.mode === 'text' && !p.preserve_line_breaks ? reflowProse(baseText || '') : (baseText || '');
  textBase.classList.toggle('hidden', !baseText?.trim() || p?.includes_command === true);
  const after = document.getElementById('question-after-figure');
  after.textContent = p?.mode === 'figure' ? p.after : '';
  after.classList.toggle('hidden', !after.textContent);
  const source = c.metadados_visual?.caminho_local_imagem;
  const visibleImage = source && mode !== 'text';
  imageContainer.classList.toggle('hidden', !visibleImage);
  imageContainer.dataset.kind = mode;
  questionImg.src = visibleImage ? (p?.figure || source) : '';
  questionImg.alt = p?.alt || c.metadados_visual?.descricao_imagem || 'Reprodução original do material de apoio. Abra para ampliar.';
  questionDescText.textContent = p?.alt || c.metadados_visual?.descricao_imagem || '';
  questionDescText.classList.add('hidden');
  btnToggleDesc.textContent = 'Descrição disponível';
  btnToggleDesc.setAttribute('aria-expanded', 'false');
  const original = document.getElementById('btn-original-source');
  original.classList.toggle('hidden', !source);
  original.dataset.src = source || '';
  enunciado.textContent = c.enunciado;
  enunciado.classList.toggle('sr-only', p?.includes_command === true);
  enunciado.style.whiteSpace = 'pre-wrap';
  closeImageViewer();

  // Alternatives
  const alternatives = q.conteudo.alternativas;
  alternativeCards.forEach(card => {
    const letter = card.dataset.letter;
    const textNode = card.querySelector('.alternative-text');
    textNode.textContent = alternatives[letter] || "Não disponível";
    card.querySelector('.alternative-visual')?.remove();
    const visual = p?.options?.[letter];
    textNode.classList.toggle('sr-only', Boolean(visual));
    if (visual) {
      const panel = document.createElement('div');
      panel.className = 'alternative-visual';
      const img = document.createElement('img');
      img.src = visual.image;
      img.alt = visual.alt || 'Alternativa ' + letter + ': reprodução oficial';
      const zoom = document.createElement('button');
      zoom.type = 'button';
      zoom.textContent = 'Ampliar alternativa ' + letter;
      zoom.addEventListener('click', event => {
        event.stopPropagation();
        openImageViewer(img.src, img.alt);
      });
      panel.append(img, zoom);
      card.append(panel);
    }
    
    // Reset classes
    card.className = 'alternative-card';
    card.setAttribute('aria-pressed','false');
    card.setAttribute('aria-disabled','false');
    card.setAttribute('aria-label', 'Alternativa ' + letter + ': ' + (alternatives[letter] || ''));
  });
  
  // Reset Action Buttons
  btnSubmit.classList.remove('hidden');
  btnSubmit.setAttribute('disabled', 'true');
  btnNextQuestion.classList.add('hidden');
  
  // Hide TRI dashboard
  triDashboard.classList.add('hidden');
  
  // Reset AI explanation elements
  btnAiExplain.removeAttribute('disabled');
  btnAiExplain.textContent = "✨ Explicar com IA (Gemini)";
  aiExplanationContainer.classList.add('hidden');
  aiExplanationContent.innerHTML = "";
  
  // Scroll to top of simulator view smoothly
  document.querySelector('.content-panel').scrollTop = 0;
}

// 6. Submit Answer
function submitAnswer() {
  if (!activeQuestion || !selectedAlternative || activeQuestion.scoring_enabled !== true) return;
  
  const correctAlternative = activeQuestion.gabarito_oficial;
  const isCorrect = selectedAlternative === correctAlternative;
  
  // Disable alternatives selection
  alternativeCards.forEach(card => {
    card.classList.add('disabled');
    card.setAttribute('aria-disabled','true');
    const letter = card.dataset.letter;
    
    // Apply correct style to correct answer
    if (letter === correctAlternative) {
      card.classList.add('correct');
    }
    
    // Apply incorrect choice style if selected wrong
    if (letter === selectedAlternative && !isCorrect) {
      card.classList.add('incorrect-choice');
    }
    
    // Mark others as incorrect
    if (letter !== correctAlternative && letter !== selectedAlternative) {
      card.classList.add('incorrect');
    }
  });
  
  // Render Feedback
  if (isCorrect) {
    answerFeedback.textContent = "Acertou! 🎉";
    answerFeedback.className = "feedback-badge success";
  } else {
    answerFeedback.textContent = `Errou! (Gabarito: ${correctAlternative}) ❌`;
    answerFeedback.className = "feedback-badge error";
  }
  
  // Render TRI Dashboard parameters
  const tri = activeQuestion.parametros_tri;
  if (!tri) {
    btnSubmit.classList.add("hidden");
    btnNextQuestion.classList.remove("hidden");
    triDashboard.classList.add("hidden");
    return;
  }
  const a = tri.a_discriminacao;
  const b = tri.b_dificuldade;
  const c = tri.c_chute;
  
  triValA.textContent = a.toFixed(3);
  triValB.textContent = b.toFixed(3);
  triValC.textContent = (c * 100).toFixed(1) + "%";
  
  // Set Gauges
  // Parameter A (Discrimination: 0.0 to 4.0 scale)
  const pctA = Math.min(Math.max((a / 4.0) * 100, 0), 100);
  gaugeBarA.style.width = `${pctA}%`;
  
  // Parameter B (Difficulty: -3.0 to +3.0 scale)
  // Coded bi-directionally from middle (50%)
  const bCapped = Math.min(Math.max(b, -3.0), 3.0);
  const pctB = (Math.abs(bCapped) / 3.0) * 50; // Max 50% width
  if (bCapped >= 0) {
    gaugeBarB.style.left = '50%';
    gaugeBarB.style.width = `${pctB}%`;
    gaugeBarB.style.backgroundColor = '#ef4444'; // Red (hot/difficult)
  } else {
    gaugeBarB.style.left = `${50 - pctB}%`;
    gaugeBarB.style.width = `${pctB}%`;
    gaugeBarB.style.backgroundColor = '#0ea5e9'; // Blue (cold/easy)
  }
  
  // Parameter C (Guessing: 0.0 to 0.35 standard maximum)
  const pctC = Math.min(Math.max((c / 0.35) * 100, 0), 100);
  gaugeBarC.style.width = `${pctC}%`;
  
  // Toggle Action Buttons
  btnSubmit.classList.add('hidden');
  btnNextQuestion.classList.remove('hidden');
  
  // Show TRI Dashboard
  triDashboard.classList.remove('hidden');
  
  // Scroll down to dashboard
  setTimeout(() => {
    triDashboard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

// 7. Toggle the available source description
function toggleIaDescription() {
  if (questionDescText.classList.contains('hidden')) {
    questionDescText.classList.remove('hidden');
    btnToggleDesc.textContent = "Ocultar descrição";
  } else {
    questionDescText.classList.add('hidden');
    btnToggleDesc.textContent = 'Descrição disponível';
  }
}

// 8. Fetch AI explanation from server
async function getAiExplanation() {
  if (!activeQuestion) return;
  
  btnAiExplain.setAttribute('disabled', 'true');
  btnAiExplain.textContent = "✨ Gerando explicação...";
  
  try {
    const res = await fetch(`${API_URL}/questions/${activeQuestion._key}/explain`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        selected: selectedAlternative
      })
    });
    
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.error || "Erro na geração do Gemini.");
    }
    
    const data = await res.json();
    
    // Parse markdown and inject
    aiExplanationContent.innerHTML = parseMarkdown(data.explanation);
    aiExplanationContainer.classList.remove('hidden');
    
    // Scroll smoothly to the explanation
    setTimeout(() => {
      aiExplanationContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
    
  } catch (err) {
    console.error("Erro ao obter explicação da IA:", err);
    aiExplanationContent.innerHTML = `<p style="color:var(--error-color);">❌ Falha ao gerar explicação: ${err.message}</p>`;
    aiExplanationContainer.classList.remove('hidden');
  } finally {
    btnAiExplain.removeAttribute('disabled');
    btnAiExplain.textContent = "✨ Explicar com IA (Gemini)";
  }
}

// Simple Markdown parser for bolding, bullet points and paragraphs
function parseMarkdown(md) {
  // Escape HTML tags to prevent security issues (XSS)
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  
  // Format bold headers (**Análise...**)
  html = html.replace(/^\*\*(.*?)\*\*$/gm, "<strong>$1</strong>");
  
  // Inline bolding
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  
  // Bullets
  html = html.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
  
  // Wrap li groups in ul tags
  html = html.replace(/(<li>.*<\/li>)/g, "<ul>$1</ul>");
  html = html.replace(/<\/ul>\s*<ul>/g, "");
  
  // Parse paragraphs
  html = html.split('\n\n').map(part => {
    const trimmed = part.trim();
    if (trimmed.startsWith('<ul>') || trimmed.startsWith('<strong>') || trimmed.startsWith('<li>')) {
      return part;
    }
    return `<p>${part.replace(/\n/g, '<br>')}</p>`;
  }).join('');
  
  return html;
}

// Startup
document.addEventListener('DOMContentLoaded', init);

// Floating Text Highlighter Logic
const highlighterBtn = document.getElementById('highlighter-btn');

document.addEventListener('mouseup', handleTextSelection);
document.addEventListener('mousedown', (e) => {
  // Hide highlighter button if clicking elsewhere
  if (e.target !== highlighterBtn) {
    highlighterBtn.classList.add('hidden');
  }
});

highlighterBtn.addEventListener('click', applyHighlight);

function handleTextSelection(e) {
  const selection = window.getSelection();
  const text = selection.toString().trim();
  
  if (!text) {
    highlighterBtn.classList.add('hidden');
    return;
  }
  
  // Ensure selection is inside textBase or enunciado
  try {
    const range = selection.getRangeAt(0);
    const startContainer = range.startContainer.parentElement;
    const endContainer = range.endContainer.parentElement;
    
    const isTextBase = textBase && (textBase.contains(startContainer) || textBase.contains(endContainer));
    const isEnunciado = enunciado && (enunciado.contains(startContainer) || enunciado.contains(endContainer));
    
    if (!isTextBase && !isEnunciado) {
      highlighterBtn.classList.add('hidden');
      return;
    }
    
    // Position button above selection
    const rect = range.getBoundingClientRect();
    highlighterBtn.style.top = `${rect.top - 48 + window.scrollY}px`;
    highlighterBtn.style.left = `${rect.left + rect.width / 2 - 19 + window.scrollX}px`;
    highlighterBtn.classList.remove('hidden');
  } catch (err) {
    highlighterBtn.classList.add('hidden');
  }
}

function applyHighlight() {
  const selection = window.getSelection();
  if (!selection.rangeCount) return;
  
  const range = selection.getRangeAt(0);
  const mark = document.createElement('mark');
  mark.className = 'highlight';
  
  try {
    range.surroundContents(mark);
  } catch (err) {
    // If selection crosses nodes, extract and wrap the contents
    try {
      const fragment = range.extractContents();
      mark.appendChild(fragment);
      range.insertNode(mark);
    } catch (fallbackErr) {
      console.warn("Could not wrap complex selection:", fallbackErr);
    }
  }
  
  selection.removeAllRanges();
  highlighterBtn.classList.add('hidden');
}

let imageTrigger = null;
function openImageViewer(src, alt) {
  imageTrigger = document.activeElement;
  const dialog = document.getElementById('image-viewer');
  document.getElementById('viewer-image').src = src;
  document.getElementById('viewer-image').alt = alt;
  document.getElementById('viewer-original-link').href = src;
  document.getElementById('image-zoom').checked = false;
  dialog.classList.remove('original-size');
  dialog.showModal();
  document.getElementById('btn-close-image').focus();
}
function closeImageViewer() {
  const dialog = document.getElementById('image-viewer');
  if(dialog?.open) dialog.close();
}

// Reflow only explicitly reviewed prose; preserve blank paragraphs and bullet lists.
function reflowProse(text) {
  return text.split(/\n\s*\n/).map(paragraph => paragraph.trim().split('\n').map(line=>line.trim()).reduce((out,line,i)=>out+(i?(line.startsWith('•')?'\n':' '):'')+line,'')).join('\n\n');
}
