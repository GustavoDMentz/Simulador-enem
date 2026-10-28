'use strict';
// Experimental 3PL EAP estimator. Reference: INEP microEnem.
// Numerical quadrature here is approximate, pending reproduction of official mirt settings.
const D=1;
function probability(theta,{a,b,c}){
 if(![theta,a,b,c].every(Number.isFinite)||a<=0||c<0||c>=1)throw Error('Invalid 3PL parameters');
 const z=D*a*(theta-b),sigmoid=z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));
 return Math.min(1-1e-12,Math.max(1e-12,c+(1-c)*sigmoid));
}
function estimateEAP(items){
 if(!Array.isArray(items)||items.length===0)throw Error('No answered items');
 const nodes=40,low=-4,high=4,step=(high-low)/(nodes-1);
 const values=[];
 for(let i=0;i<nodes;i++){
  const theta=low+i*step;
  let logWeight=-theta*theta/2;
  for(const item of items){
   if(typeof item.correct!=='boolean')throw Error('Invalid response');
   const p=probability(theta,item);
   logWeight+=item.correct?Math.log(p):Math.log1p(-p);
  }
  values.push({theta,logWeight});
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
if(typeof module!=='undefined')module.exports={probability,estimateEAP};
