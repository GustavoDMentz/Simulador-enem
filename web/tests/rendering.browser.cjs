'use strict';
const assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const {chromium}=require('playwright');
const app=require('../server');
const cases=['2024_AZUL_D2_Q137','2024_AZUL_D2_Q155','2018_AZUL_D1_Q74','2018_AZUL_D2_Q110','2024_AZUL_D2_Q111'];
const output=process.env.ENEM_RENDER_SCREENSHOTS;
(async()=>{
 const servers=[];let browser;const report={viewports:[],errors:[]};
 try{
  const server=app.listen(0,'127.0.0.1');servers.push(server);await new Promise(r=>server.on('listening',r));const base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true,executablePath:process.env.ENEM_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  let beforeBase;
  if(process.env.ENEM_BEFORE_ROOT){const old=require(path.join(process.env.ENEM_BEFORE_ROOT,'web/server'));const s=old.listen(0,'127.0.0.1');servers.push(s);await new Promise(r=>s.on('listening',r));beforeBase='http://127.0.0.1:'+s.address().port}
  for(const [name,viewport] of [['desktop',{width:1280,height:1000}],['mobile',{width:390,height:844}]]){
   const page=await browser.newPage({viewport});page.on('pageerror',e=>report.errors.push(e.message));await page.goto(base);await page.waitForSelector('.list-item');await page.waitForFunction(()=>activeQuestion?.scoring_enabled===true);
   assert.equal((await (await page.request.get(base+'/api/metadata')).json()).total,509);
   for(const id of cases){
    const q=await (await page.request.get(base+'/api/questions/'+id)).json();await page.evaluate(q=>displayQuestion(q),q);
    const text=['2024_AZUL_D2_Q137','2018_AZUL_D2_Q110','2024_AZUL_D2_Q111'].includes(id);
    assert.equal(await page.locator('#question-image-container').isVisible(),!text);
    assert.equal(await page.locator('#question-text-base').isVisible(),text||id==='2024_AZUL_D2_Q155');
    if(!text){
     await page.waitForFunction(()=>document.querySelector('#question-img').naturalWidth>0);
     const box=await page.locator('#question-img').boundingBox();assert(box.width>(name==='mobile'?250:500));
     if(id==='2018_AZUL_D1_Q74')assert(box.height>280,'Historical source remains legible');
     if(id==='2024_AZUL_D2_Q155'){assert.match(await page.locator('#question-after-figure').innerText(),/70 m²/);assert.match(await page.locator('#question-after-figure').innerText(),/90° e R = 10 m/)}
     await page.locator('#btn-enlarge-image').focus();await page.keyboard.press('Enter');assert(await page.locator('#image-viewer').isVisible());
     assert.equal(await page.locator('#btn-close-image').evaluate(e=>e===document.activeElement),true);
     await page.locator('#image-zoom').check();assert(await page.locator('#image-viewer').evaluate(e=>e.classList.contains('original-size')));
     await page.keyboard.press('Escape');assert.equal(await page.locator('#image-viewer').isVisible(),false);assert.equal(await page.locator('#btn-enlarge-image').evaluate(e=>e===document.activeElement),true);
    }
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    const correct=page.locator('.alternative-card[data-letter="'+q.gabarito_oficial+'"]');await correct.focus();await page.keyboard.press(' ');assert.equal(await correct.getAttribute('aria-pressed'),'true');await page.locator('#btn-submit').click();assert.match(await page.locator('#answer-feedback').innerText(),/Acertou/);
    await page.evaluate(q=>displayQuestion(q),q);
    if(output){
     fs.mkdirSync(output,{recursive:true});
     // Expand only the scroll container for complete, inspectable evidence captures.
     const style=await page.addStyleTag({content:'html,body{height:auto!important;overflow:visible!important}.app-container,.workspace{height:auto!important;overflow:visible!important}.content-panel{overflow:visible!important}'});
     await page.locator('.question-card').screenshot({path:path.join(output,`${name}-${id}-after.png`)});await style.evaluate(e=>e.remove());
    }
   }
   // Source remains available for text-only cases too, with native dialog focus trap.
   await page.locator('#btn-original-source').click();assert(await page.locator('#image-viewer').isVisible());await page.keyboard.press('Escape');
   report.viewports.push({name,cases:cases.length,keyboard_answer:true,zoom:true,focus_return:true,no_horizontal_overflow:true});await page.close();
   if(beforeBase&&output&&name==='desktop'){
    const p=await browser.newPage({viewport});await p.goto(beforeBase);await p.waitForSelector('.list-item');await p.waitForFunction(()=>activeQuestion?.scoring_enabled===true);
    for(const id of cases){const q=await(await p.request.get(beforeBase+'/api/questions/'+id)).json();await p.evaluate(q=>displayQuestion(q),q);await p.waitForFunction(()=>{const i=document.querySelector('#question-img');return i.complete&&i.naturalWidth>0});const style=await p.addStyleTag({content:'html,body{height:auto!important;overflow:visible!important}.app-container,.workspace{height:auto!important;overflow:visible!important}.content-panel{overflow:visible!important}'});await p.locator('.question-card').screenshot({path:path.join(output,`desktop-${id}-before.png`)});await style.evaluate(e=>e.remove())}await p.close();
   }
  }
  assert.deepEqual(report.errors,[]);console.log(JSON.stringify(report,null,2));
 }finally{if(browser)await browser.close();for(const s of servers)await new Promise(r=>s.close(r))}
})().catch(e=>{console.error(e);process.exitCode=1});
