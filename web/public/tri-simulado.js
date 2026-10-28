'use strict';
let questions=[],answers=[],index=0,selected=null;
const $=id=>document.getElementById(id);
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
$('start').addEventListener('click',async()=>{
 $('result').textContent='Carregando questões…';$('exam').hidden=true;$('summary').hidden=true;
 try{
  const area=$('area').value,count=45,year=$('year').value,all=[];
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
  if(eligible.length<count)throw Error('Somente '+eligible.length+' questões elegíveis nesta área e ano. Para iniciar, escolha outro ano ou a opção Todos os anos.');
  questions=eligible.slice(0,count);answers=[];index=0;selected=null;
  $('result').textContent='';$('setup').hidden=true;$('workspace').hidden=false;$('exam').hidden=false;render();
 }catch(e){$('result').textContent=e.message;}
});
function render(){
 const q=questions[index];selected=null;$('next').disabled=true;
 $('progress').textContent='Questão '+(index+1)+' de '+questions.length+' · '+q.ano;
 $('progress-percent').textContent=Math.round(index/questions.length*100)+'% concluído';
 $('progress-fill').style.width=(index/questions.length*100)+'%';
 $('progress-bar').setAttribute('aria-valuenow',String(index));
 $('next').textContent=index===questions.length-1?'Finalizar e ver resultado':'Confirmar e continuar →';
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
 if(index<questions.length){render();window.scrollTo?.({top:0,behavior:'smooth'});return;}
 $('exam').hidden=true;$('summary').hidden=false;
 const eap=estimateEAP(answers);
 const years=[...new Set(questions.map(q=>q.ano))];
 const calibration={LC:{origin:499.978,scale:108.086},CH:{origin:501.489,scale:112.310},CN:{origin:501.144,scale:113.102},MT:{origin:500.020,scale:129.646}};
 const {origin,scale}=calibration[$('area').value];
 const estimate=origin+scale*eap.theta;
 const uncertainty=1.2815515655446004*scale*eap.posteriorSD;
 const roundTen=n=>Math.round(n/10)*10;
 const context=years.length>1?' Anos misturados: comparabilidade dos parâmetros não demonstrada.':' Ano '+years[0]+'.';
 $('result-score').textContent=eap.correct+' / '+eap.answered+' acertos';
 $('result-range').textContent='Estimativa central: '+roundTen(estimate)+' pontos · faixa aproximada: '+roundTen(estimate-uncertainty)+'–'+roundTen(estimate+uncertainty);
 $('result-meta').textContent='Intervalo posterior aproximado de 80%, arredondado às dezenas. Proficiência EAP θ = '+eap.theta.toFixed(2)+'. Transformação origem + escala × θ (Jaloto, 2023).'+context;
 window.scrollTo?.({top:0,behavior:'smooth'});
});

$('again').addEventListener('click',()=>{questions=[];answers=[];index=0;selected=null;$('workspace').hidden=true;$('summary').hidden=true;$('setup').hidden=false;$('result').textContent='';window.scrollTo?.({top:0,behavior:'smooth'});});
