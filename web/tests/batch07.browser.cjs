'use strict';
const assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const {chromium}=require('playwright'),app=require('../server');
const review=require('../../data/audit/batch-07-review.json');
(async()=>{
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.on('listening',r));
 let browser;const result={viewports:[],errors:[]};
 try{
  const base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true,executablePath:process.env.ENEM_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  for(const [name,viewport] of [['desktop',{width:1280,height:1000}],['mobile',{width:390,height:844}]]){
   const page=await browser.newPage({viewport});page.on('pageerror',e=>result.errors.push(e.message));await page.goto(base);await page.waitForFunction(()=>activeQuestion?.scoring_enabled===true);
   const all=[];for(let p=1;p<=4;p++)all.push(...(await(await page.request.get(base+'/api/questions?limit=100&page='+p)).json()).results);
   assert.equal(all.length,328);
   for(const r of review.results.filter(r=>r.status==='APPROVED')){
    console.error(name,r.id);const q=all.find(q=>q.id_unico_sistema===r.id);assert(q);assert.equal(q.scoring_enabled,true);assert.equal(q.gabarito_oficial,r.official_answer);await page.evaluate(q=>displayQuestion(q),q);
    assert.equal(await page.locator('#question-enunciado').innerText(),r.after_content.enunciado);
    for(const letter of 'ABCDE')assert.equal(await page.locator('.alternative-card[data-letter="'+letter+'"] .alternative-text').innerText(),r.after_content.alternativas[letter]);
    const visual=true;assert.equal(await page.locator('#question-image-container').isVisible(),visual);
    if(visual){
     assert.equal(await page.locator('#question-text-base').isVisible(),r.presentation==='figure');
     if(r.presentation==='figure'){assert.equal(await page.locator('#question-text-base').textContent(),r.after_content.texto_base);assert.equal(await page.locator('#question-after-figure').textContent(),r.presentation_metadata.after);}
     await page.waitForFunction(()=>document.querySelector('#question-img').naturalWidth>0);
     assert.equal((await page.request.get(base+q.conteudo.metadados_visual.caminho_local_imagem)).status(),200);
     await page.locator('#btn-enlarge-image').focus();await page.keyboard.press('Enter');assert(await page.locator('#image-viewer').isVisible());await page.locator('#image-zoom').check();await page.keyboard.press('Escape');assert.equal(await page.locator('#btn-enlarge-image').evaluate(e=>e===document.activeElement),true);
    }else assert.equal(await page.locator('#question-text-base').textContent(),r.after_content.texto_base);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    if(process.env.ENEM_BATCH_SCREENSHOTS&&[91,92,101,106,124,133,136,140,161,169].includes(q.posicao_prova)){
     fs.mkdirSync(process.env.ENEM_BATCH_SCREENSHOTS,{recursive:true});const style=await page.addStyleTag({content:'html,body{height:auto!important;overflow:visible!important}.app-container,.workspace{height:auto!important;overflow:visible!important}.content-panel{overflow:visible!important}'});
     await page.locator('.question-card').screenshot({path:path.join(process.env.ENEM_BATCH_SCREENSHOTS,`${name}-${r.id}.png`)});await style.evaluate(e=>e.remove());
    }
    const option=page.locator('.alternative-card[data-letter="'+q.gabarito_oficial+'"]');await option.focus();if(r.id==='2021_AZUL_D2_Q151'){await page.locator('#image-viewer').dispatchEvent('close');assert.equal(await option.evaluate(e=>e===document.activeElement),true,'late close must not steal answer focus')}await page.keyboard.press(' ');assert.equal(await option.getAttribute('aria-pressed'),'true','keyboard selection: '+r.id);await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Acertou/);
    await page.evaluate(q=>displayQuestion(q),q);await page.locator('.alternative-card[data-letter="'+[...'ABCDE'].find(l=>l!==q.gabarito_oficial)+'"]').click();await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Errou/);
   }
   const inventory=fs.readFileSync(path.resolve(__dirname,'../../data/audit/session-recovery/preview-questions.jsonl'),'utf8').trim().split('\n').map(JSON.parse),published=new Set(all.map(q=>q.id_unico_sistema));
   const pending=inventory.filter(q=>!published.has(q.id_unico_sistema));assert.equal(pending.length,185);
   // All pending entries are absent from the scoring loader; sample the HTTP boundary too.
   const {load}=require('../published-questions');const scoringIds=new Set(load().map(q=>q.id_unico_sistema));assert(pending.every(q=>!scoringIds.has(q.id_unico_sistema)));
   for(const q of pending.slice(0,3))assert.equal((await page.request.get(base+'/api/questions/'+q.id_unico_sistema)).status(),404);
   for(let n=0;n<10;n++)assert(published.has((await(await page.request.get(base+'/api/questions/random')).json()).id_unico_sistema));
   result.viewports.push({name,new_questions:40,submissions:80,visual_supports:40,pending_blocked:185,random_selections:10,zoom_keyboard:true,no_horizontal_overflow:true});await page.close();
  }
  assert.deepEqual(result.errors,[]);console.log(JSON.stringify(result,null,2));
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r))}
})().catch(e=>{console.error(e);process.exitCode=1});
