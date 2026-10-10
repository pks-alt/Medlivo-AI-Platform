"use client";
import {useEffect,useMemo,useState} from "react";

async function get(path:string){const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);return b}
const stage=(x:any)=>x.placement?.actual_start_date||x.placement?.placement_status==="started"?"Started":x.placement?"Placement":x.offer?"Offer":x.interview?"Interview":"Submitted";
const riskLabel=(x:any)=>String(x?.start_readiness?.risk_level||"unknown").replaceAll("_"," ");
const fmt=(v:any)=>v?new Date(v).toLocaleDateString():"—";

export default function FunnelPage(){
 const[me,setMe]=useState<any>(null),[data,setData]=useState<any>(null),[error,setError]=useState("");
 const[filter,setFilter]=useState("All");
 useEffect(()=>{Promise.all([get("me"),get("funnel?limit=200")]).then(([m,d])=>{setMe(m);setData(d)}).catch(e=>setError(e.message))},[]);
 const items=useMemo(()=>{const all=data?.items||[];const ordered=[...all].sort((a:any,b:any)=>{
  const riskRank:Record<string,number>={critical:5,high:4,medium:3,low:2,unknown:1};
  const rank=(x:any)=>riskRank[String(x?.start_readiness?.risk_level||"unknown")]||0;
  return rank(b)-rank(a);
 });return filter==="All"?ordered:ordered.filter((x:any)=>stage(x)===filter)},[data,filter]);
 if(error)return <main className="page"><div className="adminError"><b>Funnel unavailable</b><span>{error}</span></div></main>;
 if(!data||!me)return <main className="page"><div className="adminLoading">Loading recruiting funnel…</div></main>;
 const t=data.totals||{};
 return <main className="page funnelPage">
  <div className="pageHead"><div><small>Submission to Start</small><h1>Recruiting Funnel</h1><p>{me.business_role==="recruiter"?"Your submitted candidates and starts.":me.business_role==="delivery_manager"?"Your teams’ submitted candidates and starts.":"Company-wide submitted candidates and starts."}</p></div><div className="pageActions"><a href="/">Today</a>{me.business_role!=="recruiter"&&<a href="/manager">Manager</a>}</div></div>
  <div className="funnelMetrics">
   <article><strong>{t.submissions??0}</strong><b>Submitted</b><span>JobDiva source</span></article>
   <article><strong>{t.interviews??0}</strong><b>Interview</b><span>Latest interview activity</span></article>
   <article><strong>{t.offers??0}</strong><b>Offer</b><span>Offer activity</span></article>
   <article><strong>{t.placements??0}</strong><b>Placement</b><span>Placement records</span></article>
   <article><strong>{t.starts??0}</strong><b>Started</b><span>Confirmed starts</span></article>
   <article className={(t.at_risk_starts??0)>0?"riskMetric":""}><strong>{t.at_risk_starts??0}</strong><b>At-Risk Starts</b><span>High / critical risk</span></article>
  </div>
  <section className="funnelToolbar">
   <div><b>Pipeline</b><span>At-risk starts are shown first.</span></div>
   <div className="funnelFilters">{["All","Submitted","Interview","Offer","Placement","Started"].map(x=><button key={x} className={filter===x?"active":""} onClick={()=>setFilter(x)}>{x}</button>)}</div>
  </section>
  <section className="panelBox">
   {items.length?<div className="funnelList">{items.map((x:any)=><article key={x.id} className={"funnelRow risk-"+(x.start_readiness?.risk_level||"unknown")}>
    <div className="funnelPerson"><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · {[x.job_city,x.job_state].filter(Boolean).join(", ")||"Location pending"}</span><small>{x.recruiter_name||"Recruiter"}</small></div>
    <div><span className="funnelStage">{stage(x)}</span><small>Submitted {fmt(x.submitted_at)}</small></div>
    <div><b>{x.interview?.source_status?String(x.interview.source_status).replaceAll("_"," "):"—"}</b><span>Interview</span></div>
    <div><b>{x.offer?.source_status?String(x.offer.source_status).replaceAll("_"," "):"—"}</b><span>Offer</span></div>
    <div><b>{x.placement?.planned_start_date||"—"}</b><span>Planned Start</span></div>
    <div className={"riskBadge "+(x.start_readiness?.risk_level||"unknown")}><b>{riskLabel(x)}</b><span>{x.start_readiness?.status?String(x.start_readiness.status).replaceAll("_"," "):"Not assessed"}</span></div>
    <a className="funnelOpen" href={"/funnel/"+x.job_id+"/"+x.candidate_id}>Open</a>
   </article>)}</div>:<div className="emptyState">No JobDiva submission records are available in this scope yet.</div>}
  </section>
 </main>
}
