"use client";
import {useEffect,useMemo,useState} from "react";

async function get(path:string){const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);return b}
const started=(x:any)=>Boolean(x.placement?.actual_start_date||x.placement?.placement_status==="started");
const stage=(x:any)=>started(x)?"Started":x.placement?"Placement":x.offer?"Offer":x.interview?"Interview":"Submitted";
const risk=(x:any)=>String(x?.start_readiness?.risk_level||"unknown");
const label=(v:any)=>String(v||"").replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const fmt=(v:any)=>v?new Date(v).toLocaleDateString():"—";
const pct=(a:number,b:number)=>b>0?Math.round((a/b)*100):0;
const daysSince=(v:any)=>{if(!v)return null;const d=new Date(v);if(Number.isNaN(d.getTime()))return null;return Math.max(0,Math.floor((Date.now()-d.getTime())/86400000))};
const daysUntil=(v:any)=>{if(!v)return null;const d=new Date(v+"T12:00:00");if(Number.isNaN(d.getTime()))return null;return Math.ceil((d.getTime()-Date.now())/86400000)};
const latestStageDate=(x:any)=>started(x)?x.placement?.actual_start_date:x.placement?.source_updated_at||x.placement?.synced_at||x.offer?.accepted_at||x.offer?.offered_at||x.interview?.completed_at||x.interview?.scheduled_at||x.submitted_at;
const startingSoon=(x:any)=>{const n=daysUntil(x.placement?.planned_start_date);return !started(x)&&n!==null&&n>=0&&n<=14};
const stale=(x:any)=>{const n=daysSince(latestStageDate(x));return n!==null&&n>=5&&!started(x)};
const hasRisk=(x:any)=>["high","critical"].includes(risk(x))||x.start_readiness?.status==="blocked"||stale(x);
const sourceFreshness=(items:any[])=>{const dates=items.map(x=>x.source_updated_at||x.synced_at).filter(Boolean).map(x=>new Date(x).getTime()).filter(Number.isFinite);return dates.length?new Date(Math.max(...dates)).toLocaleString():"No JobDiva records received"};

export default function FunnelPage(){
 const[me,setMe]=useState<any>(null),[data,setData]=useState<any>(null),[error,setError]=useState("");
 const[filter,setFilter]=useState("All");
 useEffect(()=>{Promise.all([get("me"),get("funnel?limit=200")]).then(([m,d])=>{setMe(m);setData(d)}).catch(e=>setError(e.message))},[]);
 const all=data?.items||[];
 const items=useMemo(()=>{const ordered=[...all].sort((a:any,b:any)=>{
  const rr:Record<string,number>={critical:6,high:5,medium:4,low:2,unknown:1};
  const ar=(hasRisk(a)?20:0)+(startingSoon(a)?5:0)+(rr[risk(a)]||0);
  const br=(hasRisk(b)?20:0)+(startingSoon(b)?5:0)+(rr[risk(b)]||0);
  return br-ar;
 });if(filter==="All")return ordered;if(filter==="At Risk")return ordered.filter(hasRisk);if(filter==="Starting Soon")return ordered.filter(startingSoon);return ordered.filter((x:any)=>stage(x)===filter)},[data,filter]);
 if(error)return <main className="page"><div className="adminError"><b>Submission to Start unavailable</b><span>{error}</span></div></main>;
 if(!data||!me)return <main className="page"><div className="adminLoading">Loading delivery pipeline…</div></main>;
 const t=data.totals||{}, submitted=t.submissions??0, interviews=t.interviews??0, offers=t.offers??0, placements=t.placements??0, starts=t.starts??0;
 const soon=all.filter(startingSoon).length, atRisk=all.filter(hasRisk).length;
 const scope=me.business_role==="recruiter"?"Your delivery pipeline":me.business_role==="delivery_manager"?"Your teams’ delivery pipeline":"Company-wide delivery pipeline";
 return <main className="page funnelPage deliveryPipelinePage">
  <div className="pageHead"><div><small>Submission to Start</small><h1>Recruiting Delivery Pipeline</h1><p>{scope}. See what is moving, what is stuck, who owns the next step, and what needs attention before start.</p></div></div>

  <div className="pipelineStages">
   <article><strong>{submitted}</strong><b>Submitted</b><span>JobDiva submission</span></article>
   <article><strong>{interviews}</strong><b>Interview</b><span>{pct(interviews,submitted)}% from submitted</span></article>
   <article><strong>{offers}</strong><b>Offer</b><span>{pct(offers,interviews)}% from interview</span></article>
   <article><strong>{placements}</strong><b>Cleared / Placement</b><span>{pct(placements,offers)}% from offer</span></article>
   <article><strong>{soon}</strong><b>Starting Soon</b><span>Next 14 days</span></article>
   <article><strong>{starts}</strong><b>Started</b><span>{pct(starts,submitted)}% from submitted</span></article>
   <article className={atRisk>0?"riskMetric":""}><strong>{atRisk}</strong><b>At Risk</b><span>Risk, block, or stalled stage</span></article>
  </div>

  <section className="conversionStrip">
   <div><small>SUBMISSION → INTERVIEW</small><b>{pct(interviews,submitted)}%</b></div>
   <div><small>INTERVIEW → OFFER</small><b>{pct(offers,interviews)}%</b></div>
   <div><small>OFFER → START</small><b>{pct(starts,offers)}%</b></div>
   <div><small>SOURCE FRESHNESS</small><b>{sourceFreshness(all)}</b></div>
  </section>

  <section className="funnelToolbar">
   <div><b>Active delivery pipeline</b><span>At-risk and starting-soon candidates are prioritized first.</span></div>
   <div className="funnelFilters">{["All","At Risk","Submitted","Interview","Offer","Placement","Starting Soon","Started"].map(x=><button key={x} className={filter===x?"active":""} onClick={()=>setFilter(x)}>{x}</button>)}</div>
  </section>

  <section className="panelBox">
   {items.length?<div className="deliveryList">{items.map((x:any)=>{
    const age=daysSince(latestStageDate(x)),startIn=daysUntil(x.placement?.planned_start_date),r=risk(x),attention=hasRisk(x);
    return <article key={x.id} className={"deliveryRow "+(attention?"needsAttention":"")}>
     <div className="deliveryPrimary"><div className="deliveryNameLine"><b>{x.candidate_name||"Candidate"}</b><span className="funnelStage">{stage(x)==="Placement"?"Cleared / Placement":stage(x)}</span>{attention&&<span className={"riskBadge "+r}>{r==="unknown"?"Needs Attention":label(r)+" Risk"}</span>}</div><span>{x.job_title||"Job"} · {[x.job_city,x.job_state].filter(Boolean).join(", ")||"Location pending"}</span><small>{x.division||"Division pending"} · Recruiter: {x.recruiter_name||"Not assigned"}</small></div>
     <div className="deliverySignal"><small>STAGE AGE</small><b>{age===null?"—":age+" days"}</b><span>{stale(x)?"Stalled 5+ days":"Current stage"}</span></div>
     <div className="deliverySignal"><small>PLANNED START</small><b>{fmt(x.placement?.planned_start_date)}</b><span>{startIn===null?"Not scheduled":startIn<0?"Past due":startIn===0?"Today":startIn+" days"}</span></div>
     <div className="deliveryAction"><small>NEXT ACTION</small><b>{x.start_readiness?.next_action||"Not assigned"}</b><span>Due {fmt(x.start_readiness?.due_at)}</span></div>
     <div className="deliveryLinks"><a href={"/candidates/"+x.candidate_id}>Candidate 360</a><a href={"/jobs/"+x.job_id}>Job 360</a><a className="primary" href={"/funnel/"+x.job_id+"/"+x.candidate_id}>Open Delivery</a></div>
    </article>})}</div>:<div className="pipelineEmpty"><b>No Submission-to-Start records have been received for this scope.</b><p>This does not automatically mean there was no recruiting activity. It means Medlivo does not currently have JobDiva submission records available for this team or scope.</p><span>Check JobDiva data synchronization or scope before treating these counts as zero production.</span></div>}
  </section>
 </main>
}
