'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {probability,estimateEAP}=require('../public/tri-mle');
test('3PL probability monotonic with guessing asymptote',()=>{
 const p={a:1,b:0,c:.2};
 assert.ok(Math.abs(probability(0,p)-.6)<1e-12);
 assert.ok(probability(-6,p)>.2);
 assert.ok(probability(2,p)>probability(0,p));
});
test('EAP is finite for 0/45 and 45/45',()=>{
 const p={a:1,b:0,c:.2};
 const low=estimateEAP(Array.from({length:45},()=>({...p,correct:false})));
 const high=estimateEAP(Array.from({length:45},()=>({...p,correct:true})));
 assert.ok(Number.isFinite(low.theta)&&Number.isFinite(high.theta));
 assert.ok(low.theta<high.theta);
 assert.ok(low.posteriorSD>0&&high.posteriorSD>0);
});
test('EAP produces posterior uncertainty and latent theta',()=>{
 const result=estimateEAP([{a:1,b:0,c:.2,correct:true},{a:1,b:0,c:.2,correct:false}]);
 assert.ok(Number.isFinite(result.theta));
 assert.equal(result.method,'3PL_EAP_APPROXIMATION');
 assert.equal(result.scale,'LATENT_THETA_NOT_ENEM_SCORE');
});
test('invalid parameters and responses are rejected',()=>{
 assert.throws(()=>probability(0,{a:0,b:0,c:.2}),/Invalid/);
 assert.throws(()=>estimateEAP([{a:1,b:0,c:.2,correct:'A'}]),/Invalid response/);
});

test('INEP mirt parameterization uses unit logistic slope',()=>{
 const p={a:2,b:1,c:0};
 assert.ok(Math.abs(probability(0,p)-1/(1+Math.exp(2)))<1e-12);
});
