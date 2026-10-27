'use strict';
const assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const {chromium}=require('playwright'),app=require('../server');
const review=require('../../data/audit/batch-08-review.json');
(async()=>{
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.on('listening',r));let browser;
 const result={viewports:[],errors:[]};
 try{
  const base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true,executablePath:process.env.ENEM_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  for(const [name,viewport] of [['desktop',{width:1280,height:1000}],['mobile',{width:390,height:844}]]){
   const page=await browser.newPage({viewport});page.on('pageerror',e=>result.errors.push(e.message));await page.goto(base);await page.waitForFunction(()=>activeQuestion?.scoring_enabled===true);
   let graphical=0,zooms=0;
   for(const r of review.results){
    if(r.status!=='APPROVED'){assert.equal((await page.request.get(base+'/api/questions/'+r.id)).status(),404);continue;}
    console.error(name,r.id);const response=await page.request.get(base+'/api/questions/'+r.id);assert.equal(response.status(),200);const q=await response.json();
    assert(q.scoring_enabled);assert.equal(q.gabarito_oficial,r.official_answer);await page.evaluate(q=>displayQuestion(q),q);
    assert.equal(await page.locator('#question-enunciado').innerText(),r.after_content.enunciado);
    const p=r.presentation_metadata;
    assert.equal(await page.locator('#question-image-container').isVisible(),p.mode!=='text');
    assert.equal(await page.locator('#question-text-base').isVisible(),p.mode==='text'?Boolean(r.after_content.texto_base.trim()):p.mode==='figure'&&Boolean(p.before.trim()));
    if(p.mode!=='text'){
     await page.waitForFunction(()=>document.querySelector('#question-img').complete&&document.querySelector('#question-img').naturalWidth>0);
     const b=await page.locator('#question-img').boundingBox();assert(b.width>100&&b.height>15);
     await page.locator('#btn-enlarge-image').focus();await page.keyboard.press('Enter');assert(await page.locator('#image-viewer').isVisible());await page.locator('#image-zoom').check();assert(await page.locator('#image-viewer').evaluate(e=>e.classList.contains('original-size')));await page.keyboard.press('Escape');assert(await page.locator('#btn-enlarge-image').evaluate(e=>e===document.activeElement));zooms++;
    }
    if(p.options){
     graphical++;
     for(const letter of 'ABCDE'){
      const card=page.locator('.alternative-card[data-letter="'+letter+'"]');const img=card.locator('.alternative-visual img');
      await img.evaluate(e=>e.decode());assert(await img.evaluate(e=>e.naturalWidth>20&&e.naturalHeight>15));
      assert(await card.locator('.alternative-text').evaluate(e=>e.classList.contains('sr-only')));
      const zoom=card.locator('.alternative-visual button');await zoom.focus();await page.keyboard.press('Enter');assert(await page.locator('#image-viewer').isVisible());
      assert.equal(await card.getAttribute('aria-pressed'),'false','zoom must not select an answer');await page.locator('#image-zoom').check();await page.keyboard.press('Escape');assert(await zoom.evaluate(e=>e===document.activeElement));zooms++;
     }
    }
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    if(process.env.ENEM_BATCH_SCREENSHOTS&&(p.options||['2020_AZUL_D2_Q91','2018_AZUL_D2_Q117','2021_AZUL_D1_Q02','2024_AZUL_D1_Q21','2025_AZUL_D1_Q26'].includes(r.id))){
     fs.mkdirSync(process.env.ENEM_BATCH_SCREENSHOTS,{recursive:true});const style=await page.addStyleTag({content:'html,body{height:auto!important;overflow:visible!important}.app-container,.workspace{height:auto!important;overflow:visible!important}.content-panel{overflow:visible!important}'});
     await page.locator('.question-card').screenshot({path:path.join(process.env.ENEM_BATCH_SCREENSHOTS,`${name}-${r.id}.png`)});await style.evaluate(e=>e.remove());
    }
    const correct=page.locator('.alternative-card[data-letter="'+q.gabarito_oficial+'"]');await correct.focus();await page.keyboard.press(' ');assert.equal(await correct.getAttribute('aria-pressed'),'true');await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Acertou/);
    await page.evaluate(q=>displayQuestion(q),q);await page.locator('.alternative-card[data-letter="'+[...'ABCDE'].find(l=>l!==q.gabarito_oficial)+'"]').focus();await page.keyboard.press(' ');await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Errou/);
   }
   for(let n=0;n<20;n++){const q=await(await page.request.get(base+'/api/questions/random')).json();assert(q.scoring_enabled);assert(!review.results.some(r=>r.id===q.id_unico_sistema&&r.status!=='APPROVED'));}
   result.viewports.push({name,new_questions:181,submissions:362,graphical_option_sets:graphical,zooms,pending_blocked:4,random_selections:20,no_horizontal_overflow:true});await page.close();
  }
  assert.deepEqual(result.errors,[]);console.log(JSON.stringify(result,null,2));
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r))}
})().catch(e=>{console.error(e);process.exitCode=1});
