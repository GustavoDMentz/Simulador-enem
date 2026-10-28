'use strict';
// ENEM 3PL item response probability and bounded maximum-likelihood estimation.
// D=1.7 is the conventional logistic approximation to the normal-ogive model.
const D=1.7;
function probability(theta,{a,b,c}){
 if(![theta,a,b,c].every(Number.isFinite)||a<=0||c<0||c>=1)throw Error('Invalid 3PL parameters');
 const z=D*a*(theta-b);
 const logistic=z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));
 return Math.min(1-1e-12,Math.max(1e-12,c+(1-c)*logistic));
}
function logLikelihood(theta,items){
 return items.reduce((sum,item)=>{
  const p=probability(theta,item);
  return sum+(item.correct?Math.log(p):Math.log1p(-p));
 },0);
}
function estimate(items){
 if(!Array.isArray(items)||items.length<1)throw Error('No answered items');
 const successes=items.filter(x=>x.correct).length;
 // All-correct/all-wrong sets have no finite unconstrained MLE.
 if(successes===0||successes===items.length)return {theta:null,reason:'EXTREME_RESPONSE_PATTERN',answered:items.length,correct:successes};
 let lo=-6,hi=6;
 // Golden-section maximization of the 3PL log-likelihood.
 const phi=(Math.sqrt(5)-1)/2;
 let x=hi-phi*(hi-lo),y=lo+phi*(hi-lo);
 for(let i=0;i<180;i++){
  if(logLikelihood(x,items)<logLikelihood(y,items)){lo=x;x=y;y=lo+phi*(hi-lo);}
  else{hi=y;y=x;x=hi-phi*(hi-lo);}
 }
 const theta=(lo+hi)/2;
 return {theta,answered:items.length,correct:successes,atBoundary:Math.abs(theta)>5.999,method:'3PL_MLE',scale:'LATENT_THETA_NOT_ENEM_SCORE'};
}
if(typeof module!=='undefined')module.exports={probability,logLikelihood,estimate};
