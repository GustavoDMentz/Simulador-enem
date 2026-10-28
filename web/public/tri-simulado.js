'use strict';
let questions=[],answers=[],index=0,selected=null;
const $=id=>document.getElementById(id);
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
$('start').addEventListener('click',async()=>{
 $('result').textContent='Carregando questões…';$('exam').hidden=true;
 try{
  const area=$('area').value,count=Number($('count').value),year=$('year').value,all=[];
  for(let page=1;page<=20;page++){
   const r=await fetch('/api/published/questions?area='+encodeURIComponent(area)+(year==='all'?'':'&year='+year)+'&limit=100&page='+page);
   if(!r.ok)throw Error('Não foi possível carregar questões publicadas');
   const data=await r.json();all.push(...data.results);
   if(page>=data.totalPages)break;
  }
  const eligible=all.filter(q=>q.scoring_enabled===true&&q.conteudo?.metadados_visual?.contem_imagem!==true&&q.parametros_tri&&
   ['a','b','c'].every(k=>Number.isFinite(q.parametros_tri[k]))&&
   q.parametros_tri.a>0&&q.parametros_tri.c>=0&&q.parametros_tri.c<1&&
   /^[A-E]$/.test(q.gabarito_oficial)&&q.conteudo?.alternativas);
  // Shuffle without changing the underlying published records.
  for(let i=eligible.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[eligible[i],eligible[j]]=[eligible[j],eligible[i]];}
  if(eligible.length<count)throw Error('Somente '+eligible.length+' questões elegíveis nesta área; selecione uma quantidade menor.');
  questions=eligible.slice(0,count);answers=[];index=0;selected=null;
  $('result').textContent='';$('exam').hidden=false;render();
 }catch(e){$('result').textContent=e.message;}
});
function render(){
 const q=questions[index];selected=null;$('next').disabled=true;
 $('progress').textContent='Questão '+(index+1)+' de '+questions.length+' · '+q.ano;
 $('question').textContent=[q.conteudo?.texto_base,q.conteudo?.enunciado].filter(Boolean).join('\n\n')||'Enunciado indisponível';
 const choices=$('choices');choices.replaceChildren();
 const alt=q.conteudo.alternativas;
 for(const letter of 'ABCDE'){
  const value=typeof alt[letter]==='string'?alt[letter]:alt[letter]?.texto||'';
  const label=document.createElement('label'),input=document.createElement('input');
  input.type='radio';input.name='choice';input.value=letter;
  input.addEventListener('change',()=>{selected=letter;$('next').disabled=false;});
  label.append(input,document.createTextNode(' '+letter+') '+value));choices.append(label);
 }
}
$('next').addEventListener('click',()=>{
 if(!selected)return;
 const q=questions[index];answers.push({...q.parametros_tri,correct:selected===q.gabarito_oficial});
 index++;
 if(index<questions.length){render();return;}
 $('exam').hidden=true;
 const out=estimate(answers);\n const years=[...new Set(questions.map(q=>q.ano))];\n const context=years.length>1?' Anos misturados: comparabilidade dos parâmetros não demonstrada.':' Ano '+years[0]+'.';
 $('result').textContent=out.theta===null?
  'Fim: '+out.correct+'/'+out.answered+' acertos. A MLE não possui máximo finito para este padrão extremo de respostas; θ não foi estimado.':
  'Fim: '+out.correct+'/'+out.answered+' acertos. Proficiência estimada θ = '+out.theta.toFixed(3)+(out.atBoundary?' (limite numérico atingido)':'')+(out.standardError===null?'':'. Erro-padrão aproximado de θ: '+out.standardError.toFixed(3))+'. Isto não é uma nota ENEM calibrada.'+context;
});
