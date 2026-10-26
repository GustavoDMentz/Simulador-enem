// Run explicitly with Playwright installed and ENEM_CHROMIUM pointing to Chromium.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const app=require('../server');
(async()=>{
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.on('listening',r));
 const base='http://127.0.0.1:'+server.address().port;
 let browser;
 const report={viewports:[],errors:[]};
 try{
  browser=await chromium.launch({headless:true,executablePath:process.env.ENEM_CHROMIUM||undefined,args:process.env.ENEM_CHROMIUM_ARGS?JSON.parse(process.env.ENEM_CHROMIUM_ARGS):['--no-sandbox','--disable-dev-shm-usage']});
  for(const [name,viewport] of [['desktop',{width:1280,height:900}],['mobile',{width:390,height:844}]]){
   const page=await browser.newPage({viewport});page.on('pageerror',e=>report.errors.push(e.message));
   await page.goto(base+'/');await page.waitForSelector('.list-item');
   const data=await (await page.request.get(base+'/api/questions?limit=100')).json();assert.equal(data.total,144);
   for(let n=2;n<=data.totalPages;n++){const next=await (await page.request.get(base+'/api/questions?limit=100&page='+n)).json();data.results.push(...next.results)}
   assert.equal(data.results.length,144);
   const known=new Set(data.results.map(q=>q.id_unico_sistema));
   for(let n=0;n<30;n++){const random=await (await page.request.get(base+'/api/questions/random')).json();assert(known.has(random.id_unico_sistema))}
   for(const q of data.results){
    assert.equal(q.scoring_enabled,true);assert.equal(q.parametros_tri,null);
    const details=await (await page.request.get(base+'/api/questions/'+q.id_unico_sistema)).json();assert.equal(details.id_unico_sistema,q.id_unico_sistema);
    await page.evaluate(q=>displayQuestion(q),q);
    assert.equal(await page.locator('#question-enunciado').innerText(),q.conteudo.enunciado);
    for(const letter of 'ABCDE')assert.equal(await page.locator('.alternative-card[data-letter="'+letter+'"] .alternative-text').innerText(),q.conteudo.alternativas[letter]);
    if(q.conteudo.texto_base)assert.equal(await page.locator('#question-text-base').textContent(),q.conteudo.texto_base);
    const asset=q.conteudo.metadados_visual?.caminho_local_imagem;
    if(asset){await page.waitForFunction(()=>{const i=document.getElementById('question-img');return i.complete&&i.naturalWidth>0});const response=await page.request.get(base+asset);assert.equal(response.status(),200)}
    await page.locator('.alternative-card[data-letter="'+q.gabarito_oficial+'"]').click();await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Acertou/);
    const wrong=[...'ABCDE'].find(l=>l!==q.gabarito_oficial);
    await page.evaluate(q=>displayQuestion(q),q);await page.locator('.alternative-card[data-letter="'+wrong+'"]').click();await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Errou/);
   }
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Simulator horizontal overflow');
   if(process.env.ENEM_UI_SCREENSHOTS)await page.screenshot({path:path.join(process.env.ENEM_UI_SCREENSHOTS,name+'-simulator.png'),fullPage:true});
   await page.goto(base+'/preview.html');await page.waitForFunction(()=>window.allRows?.length===513);
   const counts=await page.evaluate(()=>({approved:window.allRows.filter(q=>q.scoring_enabled).length,pending:window.allRows.filter(q=>!q.scoring_enabled).length}));assert.deepEqual(counts,{approved:144,pending:369});
   await page.locator('#question .choice').first().click();assert.equal(await page.locator('#question button.primary').isDisabled(),true);
   // Verify the recovered graph and portraits render within the same existing preview.
   await page.evaluate(()=>{index=window.allRows.findIndex(q=>q.id_unico_sistema==='2025_AZUL_D1_Q15');render()});
   await page.waitForFunction(()=>{const i=document.querySelector('#question img');return i&&i.complete&&i.naturalWidth>0});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false,'Preview horizontal overflow');
   if(process.env.ENEM_UI_SCREENSHOTS){await page.screenshot({path:path.join(process.env.ENEM_UI_SCREENSHOTS,name+'.png'),fullPage:true})}
   report.viewports.push({name,width:viewport.width,approved_checked:data.results.length,submissions:data.results.length*2,random_selections:30,accessible_text_checked:true,correct_and_wrong_answers:true,graphics_loaded:true,preview:513,pending_blocked:369});await page.close();
  }
  assert.deepEqual(report.errors,[]);
  console.log(JSON.stringify(report,null,2));
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r))}
})().catch(e=>{console.error(e);process.exitCode=1});
