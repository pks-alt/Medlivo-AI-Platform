"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function api(path:string){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
export default function MatchingPage(){
 const[mode,setMode]=useState<"job"|"candidate">("job"),[jobs,setJobs]=useState<any[]>([]),[candidates,setCandidates]=useState<any[]>([]),[error,setError]=useState("");
 useEffect(()=>{Promise.all([api("jobs?limit=100"),api("candidates?limit=100")]).then(([j,c])=>{setJobs(j.items||[]);setCandidates(c.items||[])}).catch(e=>setError(e.message))},[]);
 const topJobs=useMemo(()=>[...jobs].sort((a,b)=>(b.strong_match_count||0)-(a.strong_match_count||0)).slice(0,12),[jobs]);
 const topCandidates=useMemo(()=>[...candidates].sort((a,b)=>(b.strong_match_count||0)-(a.strong_match_count||0)).slice(0,12),[candidates]);
 if(error)return <main className="page"><div className="adminError"><b>Matching unavailable</b><span>{error}</span></div></main>;
 return <main className="page matchingPage">
  <div className="pageHead"><div><small>Evidence-backed matching</small><h1>Matching</h1><p>Hard requirements first. Weighted fit second. Open the trusted 360 record to review evidence before action.</p></div><span className="sourcePill">MEDLIVO CANONICAL DATA</span></div>
  <div className="workspaceTabs"><button className={mode==="job"?"active":""} onClick={()=>setMode("job")}>Job → Candidates</button><button className={mode==="candidate"?"active":""} onClick={()=>setMode("candidate")}>Candidate → Jobs</button></div>
  {mode==="job"?<section className="matchWorkspaceList">
   {topJobs.map(j=><article key={j.id} className="matchWorkspaceCard">
    <div><small>{j.division||"Division"} · {j.work_priority==="priority_1"?"PRIORITY 1":"PRIORITY 2"}</small><h2>{j.title}</h2><p>{[j.customer_name,j.city,j.state].filter(Boolean).join(" · ")}</p></div>
    <div className="matchWorkspaceSignals"><span><b>{j.strong_match_count??0}</b>Strong</span><span><b>{j.good_match_count??0}</b>Good</span><span><b>{j.match_readiness==="ready"?"Ready":"Review"}</b>Readiness</span></div>
    <Link href={"/jobs/"+j.id}>Review Job 360</Link>
   </article>)}
   {!topJobs.length&&<div className="emptyState">No live job records are currently available for matching.</div>}
  </section>:<section className="matchWorkspaceList">
   {topCandidates.map(c=><article key={c.id} className="matchWorkspaceCard">
    <div><small>{c.division||"Division"} · {c.relationship_status||"relationship not set"}</small><h2>{c.canonical_name||"Candidate"}</h2><p>{[c.profession,c.specialty,c.city,c.state].filter(Boolean).join(" · ")}</p></div>
    <div className="matchWorkspaceSignals"><span><b>{c.strong_match_count??0}</b>Strong jobs</span><span><b>{c.good_match_count??0}</b>Good jobs</span><span><b>{c.profile_freshness||"—"}</b>Freshness</span></div>
    <Link href={"/candidates/"+c.id}>Review Candidate 360</Link>
   </article>)}
   {!topCandidates.length&&<div className="emptyState">No live candidate records are currently available for matching.</div>}
  </section>}
  <div className="matchingGuardrail"><b>Matching guardrail</b><span>A high score never overrides a confirmed hard conflict. Unknown or stale facts remain Needs Verification.</span></div>
 </main>;
}
