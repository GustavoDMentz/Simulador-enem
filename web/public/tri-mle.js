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
 // The 3PL likelihood need not be unimodal: scan first, then refine the best peak.
 const lower=-6,upper=6,steps=1200,step=(upper-lower)/steps;
 let bestTheta=lower,bestLL=-Infinity;
 for(let i=0;i<=steps;i++){
  const theta=lower+i*step,ll=logLikelihood(theta,items);
  if(ll>bestLL){bestLL=ll;bestTheta=theta;}
 }
 let lo=Math.max(lower,bestTheta-step),hi=Math.min(upper,bestTheta+step);
 const phi=(Math.sqrt(5)-1)/2;
 let x=hi-phi*(hi-lo),y=lo+phi*(hi-lo);
 for(let i=0;i<100;i++){
  if(logLikelihood(x,items)<logLikelihood(y,items)){lo=x;x=y;y=lo+phi*(hi-lo);}
  else{hi=y;y=x;x=hi-phi*(hi-lo);}
 }
 const theta=(lo+hi)/2;
 const information=items.reduce((sum,item)=>{
  const p=probability(theta,item),z=D*item.a*(theta-item.b);
  const logistic=z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));
  const derivative=(1-item.c)*D*item.a*logistic*(1-logistic);
  return sum+derivative*derivative/(p*(1-p));
 },0);
 const standardError=information>0?1/Math.sqrt(information):null;
 return {theta,standardError,answered:items.length,correct:successes,atBoundary:Math.abs(theta)>5.995,method:'3PL_MLE',scale:'LATENT_THETA_NOT_ENEM_SCORE',confidence:'APPROXIMATE_FISHER_INFORMATION'};
}

// EAP benchmark: standard normal prior, 40 midpoint quadrature points on [-4,4].
// This is a research comparison, not a claim of exact replication of mirt quadrature.
function estimateEAP(items){
 if(!Array.isArray(items)||items.length===0)throw Error('No answered items');
 const nodes=40,low=-4,high=4,step=(high-low)/nodes;
 const values=[];
 for(let i=0;i<nodes;i++){
  const theta=low+(i+.5)*step;
  values.push({theta,logWeight:logLikelihood(theta,items)-theta*theta/2});
 }
 const max=Math.max(...values.map(x=>x.logWeight));
 let sum=0,weighted=0,second=0;
 for(const {theta,logWeight} of values){
  const weight=Math.exp(logWeight-max);
  sum+=weight;weighted+=weight*theta;second+=weight*theta*theta;
 }
 const theta=weighted/sum;
 return {theta,posteriorSD:Math.sqrt(Math.max(0,second/sum-theta*theta)),answered:items.length,
  correct:items.filter(x=>x.correct).length,method:'3PL_EAP_APPROXIMATION',scale:'LATENT_THETA_NOT_ENEM_SCORE'};
}
if(typeof module!=='undefined')module.exports={probability,logLikelihood,estimate,estimateEAP};
