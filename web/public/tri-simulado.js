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
 const eap=estimateEAP(answers);
 const years=[...new Set(questions.map(q=>q.ano))];
 const calibration={LC:{k:499.978,d:108.086},CH:{k:501.489,d:112.310},CN:{k:501.144,d:113.102},MT:{k:500.020,d:129.646}};
 const area=$('area').value;
 const {k,d}=calibration[area];
 const estimate=k*eap.theta+d;
 const uncertainty=1.2815515655446004*k*eap.posteriorSD;
 const roundTen=n=>Math.round(n/10)*10;
 const low=roundTen(estimate-uncertainty),high=roundTen(estimate+uncertainty);
 const context=years.length>1?' Anos misturados: comparabilidade dos parâmetros não demonstrada.':' Ano '+years[0]+'.';
 $('result').textContent='Fim: '+eap.correct+'/'+eap.answered+' acertos. Faixa estimada de nota TRI: '+low+'–'+high+' pontos (intervalo posterior aproximado de 80%, arredondado às dezenas). Referência central: aproximadamente '+roundTen(estimate)+' pontos. EAP θ = '+eap.theta.toFixed(2)+'. Estimativa NÃO OFICIAL; intervalo representa somente a incerteza do modelo, não um erro empírico validado. Constantes por área da Tabela 7 de estudo hospedado pelo Inep; equivalência com o arquivo do pacote microEnem ainda não verificada.'+context;
});
