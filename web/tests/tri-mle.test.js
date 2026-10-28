'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {probability,logLikelihood,estimate}=require('../public/tri-mle');
test('3PL has lower asymptote c and increases with theta',()=>{
 const p={a:1,b:0,c:.2};
 assert.ok(Math.abs(probability(0,p)-.6)<1e-12);
 assert.ok(probability(-6,p)>.2);
 assert.ok(probability(2,p)>probability(0,p));
});
test('mixed responses have finite bounded MLE and a likelihood maximum',()=>{
 const items=Array.from({length:20},(_,i)=>({a:1.2,b:(i-10)/5,c:.2,correct:i%3!==0}));
 const e=estimate(items);
 assert.ok(Number.isFinite(e.theta));
 assert.ok(logLikelihood(e.theta,items)>=logLikelihood(e.theta-.05,items)-1e-8);
 assert.ok(logLikelihood(e.theta,items)>=logLikelihood(e.theta+.05,items)-1e-8);
 assert.equal(e.scale,'LATENT_THETA_NOT_ENEM_SCORE');
});
test('extreme response patterns do not produce fabricated finite MLE',()=>{
 for(const correct of [true,false]){
  const e=estimate(Array.from({length:10},()=>({a:1,b:0,c:.2,correct})));
  assert.equal(e.theta,null);assert.equal(e.reason,'EXTREME_RESPONSE_PATTERN');
 }
});
test('invalid 3PL inputs are rejected',()=>assert.throws(()=>probability(0,{a:0,b:0,c:.2}),/Invalid/));
