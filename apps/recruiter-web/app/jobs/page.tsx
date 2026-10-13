"use client";

import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function load(){
 const r=await fetch("/api/team/jobs?limit=100",{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||"Jobs HTTP "+r.status);
 return b;
}
const priorityLabel=(v:any)=>{const s=String(v||"standard");if(s==="hot")return "Hot";if(s==="priority")return "High";if(s==="hold")return "On Hold";return "Standard"};
const readinessLabel=(v:any)=>v==="ready"?"Ready to Match":v==="needs_review"?"Ready with Review Items":"Not Ready";

export default function JobsPage(){
 const[data,setData]=useState<any>(null),[error,setError]=useState(""),[query,setQuery]=useState(""),[status,setStatus]=useState("Open");
 useEffect(()=>{load().then(setData).catch(e=>setError(e.message))},[]);
 const items=useMemo(()=>{
   const rows=data?.items||[];
   return rows.filter((j:any)=>{
     const q=query.trim().toLowerCase();
     const hay=[j.title,j.customer_name,j.division,j.profession,j.specialty,j.city,j.state,j.owner_name].filter(Boolean).join(" ").toLowerCase();
     if(q&&!hay.includes(q))return false;
     const s=String(j.status||"").toLowerCase();
     if(status==="Open"&&["closed","cancelled","canceled","filled"].includes(s))return false;
     if(status==="On Hold"&&!["hold","on_hold","on hold"].includes(s))return false;
     if(status==="Filled"&&s!=="filled")return false;
     if(status==="Closed"&&!["closed","cancelled","canceled"].includes(s))return false;
     return true;
   });
 },[data,query,status]);

 if(error)return <main className="page"><div className="adminError"><b>Jobs unavailable</b><span>{error}</span></div></main>;
 if(!data)return <main className="page"><div className="adminLoading">Loading Jobs...</div></main>;

 return <main className="page jobsHubPage">
  <div className="pageHead"><div><small>Demand intelligence</small><h1>Jobs</h1><p>Open requisitions, normalized requirements, match readiness and candidate demand in one place.</p></div><span className="sourcePill">JOBDIVA · READ ONLY</span></div>

  <section className="jobsHubIntro"><div><small>DIVISION JOB INTELLIGENCE</small><h2>See every active job in your authorized division.</h2><p>Assigned jobs are Priority 1. Other division jobs remain visible as Priority 2 opportunities, while JobDiva source ownership stays unchanged.</p></div><strong>{items.length}</strong></section>

  <div className="jobsHubToolbar">
    <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search job, customer, specialty, location or owner" aria-label="Search jobs"/>
    <div className="jobsStatusFilters">{["Open","On Hold","Filled","Closed","All"].map(x=><button key={x} className={status===x?"active":""} onClick={()=>setStatus(x)}>{x}</button>)}</div>
  </div>

  <div className="jobsHubList">
    {items.map((j:any)=><article key={j.id} className="jobsHubCard">
      <div className="jobsHubPrimary"><small>{j.division||"Unclassified"}{j.customer_name?" · "+j.customer_name:""}{j.work_priority?" · "+(j.work_priority==="priority_1"?"PRIORITY 1":"PRIORITY 2"):""}</small><h2>{j.title}</h2><p>{[j.profession,j.specialty,[j.city,j.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")||"Job context incomplete"}</p><span>Medlivo assignment: {j.operational_owner_name||j.owner_name||"Not assigned"} · Start {j.start_date||"pending"}{j.operational?.next_action?" · Next: "+j.operational.next_action:""}</span></div>
      <div className="jobsHubSignals">
        <span><b>{j.work_priority==="priority_1"?"Assigned":j.work_priority==="priority_2"?"Division":"—"}</b>{j.work_priority?"Work priority":"Scope"}</span>
        <span><b>{priorityLabel(j.operational?.job_priority)}</b>Manager priority</span>
        <span><b>{readinessLabel(j.match_readiness)}</b>Match readiness</span>
        <span><b>{j.strong_match_count??0}</b>Strong matches</span>
        <span><b>{j.good_match_count??0}</b>Good matches</span>
      </div>
      <div className="jobsHubFoot">
        <span>{j.requirement_count??0} requirements · {j.hard_gate_count??0} hard gates{j.shift?" · "+j.shift:""}</span>
        <Link href={"/jobs/"+j.id}>Open Job 360</Link>
      </div>
    </article>)}
    {!items.length&&<div className="emptyState">No jobs match the current search and status filters.</div>}
  </div>
 </main>;
}
