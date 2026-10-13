"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
async function session(){const r=await fetch("/api/team/session",{cache:"no-store",credentials:"same-origin"});const b=await r.json();if(!r.ok)throw new Error("Session unavailable");return b}
const daysUntil=(v:any)=>{if(!v)return null;const d=new Date(String(v).slice(0,10)+"T12:00:00");return Number.isNaN(d.getTime())?null:Math.ceil((d.getTime()-Date.now())/86400000)};
const fmtTime=(v:any)=>{if(!v)return "—";const d=new Date(v);return Number.isNaN(d.getTime())?"—":d.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})};
const label=(v:any)=>String(v||"").replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function RecruiterToday({me,data}:{me:any,data:any}){
 const[protectedData,setProtectedData]=useState<any>(data.protectedActions||{items:[]});
 const[funnel,setFunnel]=useState<any>(data.funnel||{items:[]});
 const[notice,setNotice]=useState("");
 const[busy,setBusy]=useState("");
 useEffect(()=>{if(data.protectedActions&&data.funnel)return;Promise.all([api("recruiter/protected-actions?limit=50"),api("funnel?limit=200")]).then(([p,f])=>{setProtectedData(p);setFunnel(f)}).catch(()=>{})},[data.protectedActions,data.funnel]);

 const p=data.priorities||{},d=data.dash||{},q=data.queue||{};
 const attention=useMemo(()=>[...(p.items||[])].filter((x:any)=>x.type==="follow_up"||["overdue","critical","high"].includes(String(x.urgency||"").toLowerCase())).slice(0,5),[p]);
 const p1=useMemo(()=>[...(q.items||[])].filter((x:any)=>x.work_priority==="priority_1").slice(0,5),[q]);
 const p2=useMemo(()=>[...(q.items||[])].filter((x:any)=>x.work_priority==="priority_2").slice(0,4),[q]);
 const protectedMine=useMemo(()=>[...(protectedData.items||[])].filter((x:any)=>x.is_mine&&["protected","working"].includes(x.effective_status)).slice(0,3),[protectedData]);
 const supportAvailable=useMemo(()=>[...(protectedData.items||[])].filter((x:any)=>!x.is_mine&&x.effective_status==="available_for_support").slice(0,4),[protectedData]);
 const schedule=useMemo(()=>[...(funnel.items||[])].filter((x:any)=>{
   if(!x.interview?.scheduled_at||x.interview?.completed_at)return false;
   const d=new Date(x.interview.scheduled_at),n=new Date();
   return d.getFullYear()===n.getFullYear()&&d.getMonth()===n.getMonth()&&d.getDate()===n.getDate();
 }).sort((a:any,b:any)=>new Date(a.interview.scheduled_at).getTime()-new Date(b.interview.scheduled_at).getTime()).slice(0,4),[funnel]);
 const starts=useMemo(()=>[...(funnel.items||[])].filter((x:any)=>{
   const n=daysUntil(x.placement?.planned_start_date);
   return x.placement?.planned_start_date&&!x.placement?.actual_start_date&&n!==null&&n>=0&&n<=14;
 }).sort((a:any,b:any)=>(daysUntil(a.placement.planned_start_date)??999)-(daysUntil(b.placement.planned_start_date)??999)).slice(0,4),[funnel]);
 const continueItem=attention[0]||p1[0]||null;

 async function markWorking(jobId:string){
  setBusy(jobId);setNotice("");
  try{
   const s=await session();
   const result=await api("jobs/"+jobId+"/protected-action",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({action_type:"working",source_type:"medlivo"})});
   setNotice("Marked Working. Your first-action window is satisfied and assignment remains unchanged.");
   setProtectedData((prev:any)=>({...prev,items:(prev.items||[]).map((x:any)=>x.job_id===jobId?{...x,...result,effective_status:"working"}:x)}));
  }catch(e:any){setNotice(e.message||"Could not record action")}finally{setBusy("")}
 }

 return <main className="page todayPage recruiterTodayFinal">
  <div className="pageHead"><div><small>Recruiter command center</small><h1>Today</h1><p>Urgent work first, then assigned work, schedule, recommendations and same-division opportunities.</p></div><span className="sourcePill">{me?.division||"REHABILITATION"} · RECRUITER</span></div>

  <section className="todayWelcome recruiterTodayHero"><small>YOUR DAY</small><h2>What should you work on next?</h2><p>Medlivo ranks actionability. Delivery Manager assignment remains the accountability boundary.</p></section>
  {notice&&<div className="todayDataNotice"><b>Action update</b><span>{notice}</span></div>}

  <div className="todayMetricGrid">
   <article className={attention.length?"attention":""}><strong>{attention.length}</strong><b>Needs attention</b><span>Replies, follow-ups and urgent actions</span></article>
   <article><strong>{p1.length}</strong><b>My Priority 1</b><span>Assigned jobs in this view</span></article>
   <article><strong>{p.totals?.priority_1_matches??0}</strong><b>Strong new matches</b><span>On assigned work</span></article>
   <article className={starts.some((x:any)=>["high","critical"].includes(String(x.start_readiness?.risk_level||"")) )?"attention":""}><strong>{starts.length}</strong><b>Upcoming starts</b><span>Next placements visible</span></article>
  </div>

  <section className="panelBox recruiterTodaySection"><div className="todaySectionHead"><div><small>NEEDS YOUR ATTENTION</small><h2>Handle these before routine queue work</h2></div></div>
   {attention.length?<div className="priorityList">{attention.map((x:any,i:number)=><article key={x.id||i} className={"priorityItem "+(x.urgency||"")}><div><small>{label(x.type||"action")}</small><b>{x.candidate_name||x.title||"Recruiter action"}</b><span>{x.detail||x.reason||x.urgency||"Review next action"}</span></div>{x.job_id?<Link href={"/jobs/"+x.job_id}>Continue</Link>:<Link href="/conversations">Open</Link>}</article>)}</div>:<div className="goodState">No urgent actions are currently visible. Continue your highest-ranked Priority 1 job.</div>}
  </section>

  {continueItem&&<section className="panelBox recruiterContinue"><small>CONTINUE WHERE YOU LEFT OFF</small><div><h2>{continueItem.candidate_name||continueItem.title||"Priority work"}</h2><p>{continueItem.detail||"Resume the highest-ranked current work item."}</p></div>{continueItem.job_id?<Link className="linkButton" href={"/jobs/"+continueItem.job_id}>Continue work</Link>:<Link className="linkButton" href="/conversations">Continue</Link>}</section>}

  <section className="panelBox recruiterTodaySection"><div className="todaySectionHead"><div><small>TIME-SENSITIVE ASSIGNED WORK</small><h2>Protected first-action window</h2></div><span>8 AM–5 PM Pacific · weekdays</span></div>
   {protectedMine.length?<div className="protectedActionGrid">{protectedMine.map((x:any)=><article key={x.id} className={"protectedActionCard "+x.effective_status}><div><span className="workPriorityPill">PRIORITY 1</span><h3>{x.job_title}</h3><p>{[x.city,x.state].filter(Boolean).join(", ")} · Assigned to {x.assigned_recruiter_name||"you"}</p><small>{x.effective_status==="working"?"Working":String(x.remaining_business_minutes??0)+" working minutes remaining"} · assignment protected</small></div><div className="protectedActionButtons">{x.effective_status==="protected"&&<button disabled={busy===x.job_id} onClick={()=>markWorking(x.job_id)}>{busy===x.job_id?"Saving…":"Mark Working"}</button>}<Link href={"/jobs/"+x.job_id}>Open Job 360</Link></div></article>)}</div>:<div className="emptyState">No active protected first-action window is currently visible.</div>}
   {supportAvailable.length>0&&<><div className="todaySupportLabel">AVAILABLE FOR SUPPORT</div><div className="protectedActionGrid support">{supportAvailable.map((x:any)=><article key={x.id} className="protectedActionCard available_for_support"><div><span className="workPriorityPill">PRIORITY 2 SUPPORT</span><h3>{x.job_title}</h3><p>Assigned to {x.assigned_recruiter_name||"another recruiter"} · assignment stays unchanged</p><small>Protected first-action window expired. Same-division support is now allowed.</small></div><div className="protectedActionButtons"><Link href={"/jobs/"+x.job_id}>Help on this job</Link></div></article>)}</div></>}
  </section>

  <section className="panelBox recruiterTodaySection"><div className="todaySectionHead"><div><small>MY PRIORITY 1 WORK</small><h2>Assigned jobs ranked by next action</h2></div><Link href="/jobs">View all My Jobs</Link></div>
   {p1.length?<div className="priorityJobGrid">{p1.map((job:any)=><article key={job.job_id}><div><small>{job.operational?.job_priority==="high"?"HIGH PRIORITY":"PRIORITY 1"}</small><h3>{job.title}</h3><p>{[job.city,job.state].filter(Boolean).join(", ")}</p></div><strong>{(job.matches||[]).length}</strong><span>candidate matches</span><Link href={"/jobs/"+job.job_id}>Work this job</Link></article>)}</div>:<div className="emptyState">No assigned Priority 1 jobs are visible.</div>}
  </section>

  <div className="todayGrid recruiterTodaySplit">
   <section className="panelBox"><div className="todaySectionHead"><div><small>TODAY'S SCHEDULE</small><h2>Interviews</h2></div><Link href="/interviews">View all</Link></div>{schedule.length?<div className="todayList">{schedule.map((x:any)=><Link key={x.id} href="/interviews"><div><b>{fmtTime(x.interview.scheduled_at)} · {x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"}</span></div><strong>Open</strong></Link>)}</div>:<div className="emptyState">No scheduled interviews are visible.</div>}</section>
   <section className="panelBox"><div className="todaySectionHead"><div><small>UPCOMING STARTS</small><h2>Start readiness</h2></div><Link href="/funnel">View all</Link></div>{starts.length?<div className="todayList">{starts.map((x:any)=><Link key={x.id} href={"/funnel/"+x.job_id+"/"+x.candidate_id}><div><b>{x.candidate_name||"Candidate"} · {daysUntil(x.placement.planned_start_date)??"—"} days</b><span>{x.job_title||"Job"} · {x.start_readiness?.status||"Readiness pending"}</span></div><strong>{String(x.start_readiness?.risk_level||"").toUpperCase()||"OPEN"}</strong></Link>)}</div>:<div className="emptyState">No upcoming starts are visible.</div>}</section>
  </div>

  <section className="panelBox recruiterTodaySection"><div className="todaySectionHead"><div><small>OPPORTUNITIES MEDLIVO FOUND</small><h2>Strong matches on your assigned work</h2></div><Link href="/matching">Review Matching</Link></div><p className="sectionHelp">Recommendations are evidence-backed and do not change Delivery Manager assignment or candidate relationship protection.</p><div className="todayRecommendation">{(p.items||[]).filter((x:any)=>x.type==="match_review"&&x.work_priority==="priority_1").slice(0,4).map((x:any,i:number)=><article key={x.id||x.match_id||i}><b>{x.candidate_name||"Candidate match"}</b><span>{x.title||x.detail||"Strong current match"}{x.score?" · score "+Number(x.score).toFixed(1):""}</span>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Review</Link>}</article>)}</div></section>

  <section className="panelBox recruiterTodaySection"><div className="todaySectionHead"><div><small>REHABILITATION OPPORTUNITIES YOU CAN HELP WITH</small><h2>Priority 2 · evidence-backed only</h2></div><Link href="/jobs">Division Opportunities</Link></div>{p2.length?<div className="priorityJobGrid">{p2.map((job:any)=><article key={job.job_id}><div><small>PRIORITY 2 · NOT ASSIGNED TO YOU</small><h3>{job.title}</h3><p>Shown because Medlivo found eligible same-division candidate opportunities.</p></div><strong>{(job.matches||[]).length}</strong><span>candidate opportunities</span><Link href={"/jobs/"+job.job_id}>Review opportunity</Link></article>)}</div>:<div className="emptyState">No additional evidence-backed division opportunities are currently visible.</div>}</section>
 </main>;
}
