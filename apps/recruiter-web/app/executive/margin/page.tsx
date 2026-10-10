"use client";
import {useEffect,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
 return body;
}
const pct=(v:any)=>(Number(v||0)*100).toFixed(1)+"%";
const money=(v:any)=>Number(v||0).toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0});
const statusLabel=(s:string)=>({
 within_guideline:"Within Guideline",
 discuss_delivery_manager:"Discuss with Delivery Manager",
 discuss_leadership:"Discuss with Leadership",
 negative_gm:"Negative GM",
 policy_unconfigured:"Guideline Not Configured",
}[s]||String(s||"").replaceAll("_"," "));

export default function ExecutiveMarginPage(){
 const[me,setMe]=useState<any>(null),[summary,setSummary]=useState<any>(null),[exceptions,setExceptions]=useState<any[]>([]);
 const[error,setError]=useState(""),[working,setWorking]=useState(""),[notes,setNotes]=useState<Record<string,string>>({});
 async function refresh(){
  const[m,s,e]=await Promise.all([api("me"),api("margin/management-summary"),api("margin/negative-gm-exceptions?status=pending&limit=100")]);
  setMe(m);setSummary(s);setExceptions(e.items||[]);
 }
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 async function decide(id:string,decision:"approved"|"rejected"){
  const note=(notes[id]||"").trim();
  if(decision==="rejected"&&note.length<3){setError("Add a reason before rejecting the exception.");return}
  setWorking(id);setError("");
  try{
   await api("margin/negative-gm-exceptions/"+id+"/decision",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({decision,notes:note||"Executive reviewed the documented negative-GM exception."})});
   await refresh();
  }catch(e:any){setError(e.message)}finally{setWorking("")}
 }

 if(error&&!summary)return <main className="page"><div className="adminError"><b>Executive margin view unavailable</b><span>{error}</span></div></main>;
 if(!summary||!me)return <main className="page"><div className="adminLoading">Loading GM overview…</div></main>;
 if(me.business_role!=="executive")return <main className="page"><div className="adminError"><b>Executive access required</b><span>This view contains company-level margin exceptions.</span></div></main>;
 const t=summary.totals||{};
 return <main className="page executiveMarginPage">
  <div className="pageHead"><div><small>Executive · Gross Margin</small><h1>GM & Rate Exceptions</h1><p>Current recruiter rate packages, finalization status and the only hard approval queue: negative GM.</p></div><div className="pageActions"><a href="/">Today</a><a href="/manager">Manager</a><a href="/admin">Admin</a></div></div>

  <div className="gmMetricGrid">
   <article><strong>{t.current_packages??0}</strong><b>Current packages</b><span>Latest version per job and candidate</span></article>
   <article><strong>{t.finalized??0}</strong><b>Finalized rates</b><span>Recruiter-finalized packages</span></article>
   <article><strong>{pct(t.average_gm_percent)}</strong><b>Average current GM</b><span>Across latest rate packages</span></article>
   <article><strong>{pct(t.finalized_average_gm_percent)}</strong><b>Finalized average GM</b><span>Across finalized rates only</span></article>
   <article><strong>{t.discussion_required??0}</strong><b>Needs discussion</b><span>Delivery Manager or leadership discussion</span></article>
   <article><strong>{t.negative_gm??0}</strong><b>Negative GM</b><span>{exceptions.length} awaiting Executive decision</span></article>
  </div>

  <section className="panelBox exceptionPanel"><small>NEGATIVE-GM EXCEPTIONS REQUIRING EXECUTIVE DECISION</small>
   {!exceptions.length?<div className="goodState">No negative-GM exceptions are waiting for Executive action.</div>:<div className="exceptionList">
    {exceptions.map((x:any)=>{
      const r=x.result_payload||{};
      return <article key={x.id} className="exceptionCard">
       <div className="exceptionHead"><div><b>{money(r.gross_margin_per_week)} / week</b><span>{pct(r.gross_margin_percent)} GM · {x.calculation_profile?.replaceAll("_"," ")}</span></div><strong>EXECUTIVE EXCEPTION</strong></div>
       <div className="exceptionNumbers"><span><b>{money(r.net_client_billing_per_week)}</b>Net billing / week</span><span><b>{money(r.total_cost_per_week)}</b>Total cost / week</span><span><b>{money(r.gross_margin_assignment)}</b>Assignment GM</span></div>
       <p>{x.reason||"Negative GM requires explicit Executive exception before recruiter finalization."}</p>
       <textarea value={notes[x.id]||""} onChange={e=>setNotes({...notes,[x.id]:e.target.value})} placeholder="Decision note or commercial rationale"/>
       <div className="exceptionActions"><button disabled={working===x.id} onClick={()=>decide(x.id,"approved")}>Approve Exception</button><button className="reject" disabled={working===x.id} onClick={()=>decide(x.id,"rejected")}>Reject</button></div>
      </article>
    })}
   </div>}
  </section>

  <section className="panelBox"><small>RECENT GM PACKAGES</small>{(summary.recent||[]).length?<table className="adminTable"><thead><tr><th>Recruiter</th><th>Profile</th><th>GM</th><th>GM / Week</th><th>Status</th><th>Lifecycle</th></tr></thead><tbody>{summary.recent.map((x:any)=><tr key={x.id}><td>{x.recruiter_name}</td><td>{String(x.calculation_profile||"").replaceAll("_"," ")}</td><td>{pct(x.result_payload?.gross_margin_percent)}</td><td>{money(x.result_payload?.gross_margin_per_week)}</td><td>{statusLabel(x.guideline_status)}</td><td>{String(x.lifecycle_status||"").replaceAll("_"," ")}</td></tr>)}</tbody></table>:<div className="emptyState">No margin packages are available yet.</div>}</section>
 </main>
}
