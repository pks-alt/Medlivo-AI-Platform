"use client";

import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function api(path:string){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
const priorityLabel=(v:any)=>{const s=String(v||"standard");if(s==="hot")return "Hot";if(s==="priority"||s==="high")return "High";if(s==="hold")return "On Hold";return "Standard"};
const readinessLabel=(v:any)=>v==="ready"?"Ready to Match":v==="needs_review"?"Ready with Review Items":"Not Ready";

export default function JobsPage(){
 const[data,setData]=useState<any>(null),[me,setMe]=useState<any>(null),[error,setError]=useState(""),[query,setQuery]=useState(""),[status,setStatus]=useState("Open"),[workMode,setWorkMode]=useState<"p1"|"p2"|"all">("p1");
 useEffect(()=>{Promise.all([api("jobs?limit=100"),api("me")]).then(([d,m])=>{setData(d);setMe(m);if(m.business_role!=="recruiter")setWorkMode("all")}).catch(e=>setError(e.message))},[]);
 const recruiter=me?.business_role==="recruiter";
 const items=useMemo(()=>{
   const rows=data?.items||[];
   return rows.filter((j:any)=>{
     const q=query.trim().toLowerCase();
     const hay=[j.title,j.customer_name,j.division,j.profession,j.specialty,j.city,j.state,j.owner_name,j.operational_owner_name].filter(Boolean).join(" ").toLowerCase();
     if(q&&!hay.includes(q))return false;
     const s=String(j.status||"").toLowerCase();
     if(status==="Open"&&["closed","cancelled","canceled","filled"].includes(s))return false;
     if(status==="On Hold"&&!["hold","on_hold","on hold"].includes(s))return false;
     if(status==="Filled"&&s!=="filled")return false;
     if(status==="Closed"&&!["closed","cancelled","canceled"].includes(s))return false;
     if(recruiter&&workMode==="p1"&&j.work_priority!=="priority_1")return false;
     if(recruiter&&workMode==="p2"&&j.work_priority!=="priority_2")return false;
     return true;
   }).sort((a:any,b:any)=>{
     const high=(x:any)=>["hot","priority","high"].includes(String(x.operational?.job_priority||""))?1:0;
     return high(b)-high(a)||(b.strong_match_count||0)-(a.strong_match_count||0);
   });
 },[data,query,status,workMode,recruiter]);

 if(error)return <main className="page"><div className="adminError"><b>Jobs unavailable</b><span>{error}</span></div></main>;
 if(!data||!me)return <main className="page"><div className="adminLoading">Loading Jobs...</div></main>;

 return <main className="page jobsHubPage finalJobsPage">
  <div className="pageHead"><div><small>Demand intelligence</small><h1>Jobs</h1><p>{recruiter?"Which job should I work next? Assigned accountability is separated from same-division opportunity.":"Open requisitions, normalized requirements, match readiness and candidate demand in one place."}</p></div><span className="sourcePill">JOBDIVA · READ ONLY</span></div>

  {recruiter&&<div className="workspaceTabs jobsWorkTabs"><button className={workMode==="p1"?"active":""} onClick={()=>setWorkMode("p1")}>My Jobs · Priority 1</button><button className={workMode==="p2"?"active":""} onClick={()=>setWorkMode("p2")}>Division Opportunities · Priority 2</button><button className={workMode==="all"?"active":""} onClick={()=>setWorkMode("all")}>All Division Jobs</button></div>}

  <section className="jobsHubIntro"><div><small>{recruiter?(workMode==="p1"?"ASSIGNED ACCOUNTABILITY":workMode==="p2"?"EVIDENCE-BACKED OPPORTUNITY":"DIVISION JOB INTELLIGENCE"):"DIVISION JOB INTELLIGENCE"}</small><h2>{recruiter&&workMode==="p1"?"Work your assigned jobs first.":recruiter&&workMode==="p2"?"Help where Medlivo found a real candidate reason.":"See every active job in your authorized scope."}</h2><p>{recruiter&&workMode==="p2"?"Priority 2 does not change the Delivery Manager's primary assignment. Candidate relationship protection still applies.":"JobDiva source ownership stays unchanged."}</p></div><strong>{items.length}</strong></section>

  <div className="jobsHubToolbar">
    <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search job, customer, specialty, location or owner" aria-label="Search jobs"/>
    <div className="jobsStatusFilters">{["Open","On Hold","Filled","Closed","All"].map(x=><button key={x} className={status===x?"active":""} onClick={()=>setStatus(x)}>{x}</button>)}</div>
  </div>

  <div className="jobsHubList">
    {items.map((j:any)=><article key={j.id} className={"jobsHubCard "+(j.work_priority==="priority_2"?"priorityTwo":"priorityOne")}>
      <div className="jobsHubPrimary"><small>{j.division||"Unclassified"}{j.customer_name?" · "+j.customer_name:""}{j.work_priority?" · "+(j.work_priority==="priority_1"?"PRIORITY 1 · ASSIGNED":"PRIORITY 2 · DIVISION OPPORTUNITY"):""}</small><h2>{j.title}</h2><p>{[j.profession,j.specialty,[j.city,j.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")||"Job context incomplete"}</p><span>{j.work_priority==="priority_2"?"Primary assignment remains with "+(j.operational_owner_name||j.owner_name||"the assigned recruiter"):"Medlivo assignment: "+(j.operational_owner_name||j.owner_name||"Not assigned")} · Start {j.start_date||"pending"}{j.operational?.next_action?" · Next: "+j.operational.next_action:""}</span></div>
      <div className="jobsHubSignals">
        <span><b>{j.work_priority==="priority_1"?"Assigned":j.work_priority==="priority_2"?"Opportunity":"—"}</b>{j.work_priority?"Work priority":"Scope"}</span>
        <span><b>{priorityLabel(j.operational?.job_priority)}</b>Manager priority</span>
        <span><b>{readinessLabel(j.match_readiness)}</b>Match readiness</span>
        <span><b>{j.strong_match_count??0}</b>Strong matches</span>
        <span><b>{j.good_match_count??0}</b>Good matches</span>
      </div>
      <div className="jobsHubFoot">
        <span>{j.requirement_count??0} requirements · {j.hard_gate_count??0} hard gates{j.shift?" · "+j.shift:""}</span>
        <Link href={"/jobs/"+j.id}>{j.work_priority==="priority_2"?"Review Opportunity":"Open Job 360"}</Link>
      </div>
    </article>)}
    {!items.length&&<div className="emptyState">{recruiter&&workMode==="p2"?"No Priority 2 opportunities currently meet the evidence-backed visibility rule.":"No jobs match the current filters."}</div>}
  </div>
 </main>;
}
